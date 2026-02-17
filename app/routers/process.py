import time
import uuid
import os
from pathlib import Path
from fastapi import APIRouter, Request
from app.models.dtos import (
    PipelineRequest,
    PipelineV2Request,
    PipelineV2ResponseOk,
    PipelineV2ResponseError,
    TemplateInfo,
    OutputUrls,
    TimingInfo,
    StepInfo,
    NoteItem,
)
from app.models.errors import ErrorCode
from app.services.template_resolver import (
    TemplateResolver,
    TemplateDownloadError,
    TemplateChecksumMismatch,
    TemplateExtractError,
    TemplateInvalidError,
)
from app.services.manifest_loader import (
    ManifestLoader,
    ManifestLoadError,
    ManifestValidationError,
)
from app.services.render_engine import RenderEngine, RenderError
from app.services.storage_manager import StorageManager, StorageError
from app.services.rules_loader import RulesLoader
from app.clients.platform_client import PlatformClient, PlatformResolveError
from app.services.segmentation.segmentation_service import SegmentationService
from app.config import settings
from PIL import Image

# v1 路由（保持兼容）
router_v1 = APIRouter(prefix="/pipeline/v1", tags=["process"])


@router_v1.post("/process")
def process(req: PipelineRequest, request: Request):
    try:
        pipeline_service = request.app.state.pipeline_service
        # PipelineService.run(req) 预计返回 Pydantic 模型（PipelineResponse）
        return pipeline_service.run(req).model_dump()
    except Exception as e:
        return {
            "ok": False,
            "steps": [],
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "internal error",
                "detail": {"reason": str(e)},
            },
        }


# v2 路由：模板驱动接口
router_v2 = APIRouter(prefix="/pipeline/v2", tags=["process_v2"])


@router_v2.post("/process")
async def process_v2(req: PipelineV2Request, request: Request):
    """
    模板驱动的图像处理入口。

    端到端流程：
    1. 生成 jobId
    2. TemplateResolver.resolve() 获取 template_dir
    3. ManifestLoader 生成 runtime_spec（并校验 assets）
    4. RenderEngine.render(raw_image) 得到 final_image
    5. StorageManager.store_preview/store_final 保存
    6. 返回 PipelineV2ResponseOk
    """
    # 生成 jobId
    job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    # 计时开始
    start_time = time.time()
    timing_steps = []
    notes = []
    warnings = []
    
    # 获取基础 URL（用于生成完整 URL）
    base_url = str(request.base_url).rstrip("/")
    if not base_url:
        base_url = settings.PUBLIC_BASE_URL
    
    try:
        # 1. 模板解析
        template_resolve_start = time.time()
        try:
            # 如果 checksum 未提供，使用占位符（TemplateResolver 需要非空字符串）
            # 注意：TemplateResolver 总是会校验，如果 checksum 为空，我们需要提供一个值
            # 但实际校验会失败，所以如果 checksum 为空，我们应该要求用户提供
            if not req.checksumSha256:
                return PipelineV2ResponseError(
                    ok=False,
                    jobId=job_id,
                    error={
                        "code": "INVALID_INPUT",
                        "message": "checksumSha256 is required for template validation",
                        "detail": {}
                    },
                    timing=TimingInfo(totalMs=int((time.time() - start_time) * 1000), steps=[]),
                    notes=[NoteItem(
                        code="ERROR_MISSING_CHECKSUM",
                        message="Template checksum is required for security validation",
                        details={}
                    )]
                ).model_dump()
            
            template_resolver = TemplateResolver(
                template_code=req.templateCode,
                version=req.versionSemver,
                download_url=req.downloadUrl,
                checksum=req.checksumSha256,
            )
            template_dir = template_resolver.resolve()
            template_resolve_ms = int((time.time() - template_resolve_start) * 1000)
            timing_steps.append(StepInfo(name="TEMPLATE_RESOLVE", ms=template_resolve_ms))
            
            # 检查是否从缓存加载
            manifest_path = Path(template_dir) / "manifest.json"
            if manifest_path.exists():
                # 检查缓存目录的创建时间（简单判断是否是新下载的）
                # 这里假设如果 manifest.json 存在且较旧，可能是缓存
                notes.append(NoteItem(
                    code="TEMPLATE_CACHED",
                    message="Template was loaded from cache",
                    details={"templateDir": template_dir}
                ))
            
            # 调试环境：添加模板目录信息
            if os.getenv("DEBUG", "").lower() in ("1", "true", "yes"):
                notes.append(NoteItem(
                    code="TEMPLATE_DIR",
                    message="Template directory path (debug only)",
                    details={"path": template_dir}
                ))
        except TemplateDownloadError as e:
            template_resolve_ms = int((time.time() - template_resolve_start) * 1000)
            timing_steps.append(StepInfo(name="TEMPLATE_RESOLVE", ms=template_resolve_ms))
            return PipelineV2ResponseError(
                ok=False,
                jobId=job_id,
                error={
                    "code": "TEMPLATE_DOWNLOAD_FAILED",
                    "message": str(e),
                    "retryable": True,
                    "detail": {"downloadUrl": req.downloadUrl}
                },
                timing=TimingInfo(totalMs=template_resolve_ms, steps=timing_steps),
                notes=[NoteItem(
                    code="ERROR_TEMPLATE_DOWNLOAD",
                    message="Template download failed",
                    details={"error": str(e)}
                )]
            ).model_dump()
        except TemplateChecksumMismatch as e:
            template_resolve_ms = int((time.time() - template_resolve_start) * 1000)
            timing_steps.append(StepInfo(name="TEMPLATE_RESOLVE", ms=template_resolve_ms))
            
            # 从错误消息中提取 expected 和 actual checksum
            error_msg = str(e)
            expected_checksum = req.checksumSha256
            actual_checksum = None
            
            # 尝试从错误消息中提取： "expected {expected}, got {actual}"
            if "expected" in error_msg and "got" in error_msg:
                try:
                    parts = error_msg.split("expected")[1].split("got")
                    if len(parts) == 2:
                        expected_checksum = parts[0].strip()
                        actual_checksum = parts[1].strip()
                except:
                    pass
            
            return PipelineV2ResponseError(
                ok=False,
                jobId=job_id,
                error={
                    "code": "TEMPLATE_CHECKSUM_MISMATCH",
                    "message": str(e),
                    "retryable": False,
                    "detail": {
                        "templateCode": req.templateCode,
                        "versionSemver": req.versionSemver,
                        "expected": expected_checksum,
                        "actual": actual_checksum
                    }
                },
                timing=TimingInfo(totalMs=template_resolve_ms, steps=timing_steps),
                notes=[NoteItem(
                    code="ERROR_CHECKSUM_MISMATCH",
                    message="Template checksum validation failed",
                    details={"error": str(e), "expected": expected_checksum, "actual": actual_checksum}
                )]
            ).model_dump()
        except (TemplateExtractError, TemplateInvalidError) as e:
            template_resolve_ms = int((time.time() - template_resolve_start) * 1000)
            timing_steps.append(StepInfo(name="TEMPLATE_RESOLVE", ms=template_resolve_ms))
            return PipelineV2ResponseError(
                ok=False,
                jobId=job_id,
                error={
                    "code": "TEMPLATE_EXTRACT_ERROR",
                    "message": str(e),
                    "detail": {"templateCode": req.templateCode}
                },
                timing=TimingInfo(totalMs=template_resolve_ms, steps=timing_steps),
                notes=[NoteItem(
                    code="ERROR_TEMPLATE_EXTRACT",
                    message="Template extraction failed",
                    details={"error": str(e)}
                )]
            ).model_dump()
        
        # 2. 加载 manifest 并生成 runtime_spec
        manifest_load_start = time.time()
        try:
            print(f"[process_v2] Starting manifest loading for template_dir={template_dir}")
            manifest_loader = ManifestLoader(template_dir)
            manifest = manifest_loader.load_manifest()
            print(f"[process_v2] Manifest loaded, starting validation...")
            manifest_loader.validate_manifest(manifest)
            print(f"[process_v2] Manifest validation passed, generating runtime_spec...")
            runtime_spec = manifest_loader.to_runtime_spec(manifest)
            print(f"[process_v2] Runtime spec generated, validating assets...")
            manifest_loader.validate_assets(runtime_spec)
            print(f"[process_v2] ✅ All manifest loading steps completed successfully")
            
            manifest_load_ms = int((time.time() - manifest_load_start) * 1000)
            timing_steps.append(StepInfo(name="MANIFEST_LOAD", ms=manifest_load_ms))
            
            # 加载 rules 配置
            rules_loader = RulesLoader(template_dir)
            rules_result = rules_loader.load(manifest)
            
            # 添加 rules 加载状态到 notes
            notes.append(NoteItem(
                code="RULES_LOADED",
                message=(
                    "Rules file loaded successfully"
                    if rules_result.rules_loaded
                    else "Rules file not loaded, using defaults"
                ),
                details={"value": rules_result.rules_loaded},
            ))
            notes.append(NoteItem(
                code="RULES_DEFAULT_USED",
                message=(
                    "Default rules used"
                    if rules_result.rules_default_used
                    else "Custom rules used"
                ),
                details={"value": rules_result.rules_default_used},
            ))
            
            # 判定是否需要 segmentation（needs_segmentation）
            # needs_cutout = any(photo.source == "cutout")
            photos = runtime_spec.get("photos", [])
            needs_cutout = any(photo.get("source") == "cutout" for photo in photos)
            
            # seg_enabled = rules.segmentation.enabled == true（默认 false）
            # 支持两种格式：
            # 1. 扁平化：{"segmentation.enabled": true}
            # 2. 嵌套：{"segmentation": {"enabled": true}}
            if "segmentation.enabled" in rules_result.rules:
                seg_enabled = rules_result.rules.get("segmentation.enabled", False) is True
            elif "segmentation" in rules_result.rules and isinstance(rules_result.rules["segmentation"], dict):
                seg_enabled = rules_result.rules["segmentation"].get("enabled", False) is True
            else:
                seg_enabled = False
            
            # needs_segmentation = needs_cutout && seg_enabled
            needs_segmentation = needs_cutout and seg_enabled
            
            # 将判定结果写入 notes
            notes.append(NoteItem(
                code="NEEDS_CUTOUT",
                message=f"Template requires cutout: {needs_cutout}",
                details={"value": needs_cutout},
            ))
            notes.append(NoteItem(
                code="SEG_ENABLED",
                message=f"Segmentation enabled in rules: {seg_enabled}",
                details={"value": seg_enabled},
            ))
            notes.append(NoteItem(
                code="NEEDS_SEGMENTATION",
                message=f"Segmentation required: {needs_segmentation}",
                details={"value": needs_segmentation},
            ))
            
            # 如果 needs_segmentation=true，调用 platform resolve 获取 execution plan
            if needs_segmentation:
                try:
                    # 从 rules 中提取参数
                    # 支持两种格式：扁平化 {"segmentation.prefer": [...]} 或嵌套 {"segmentation": {"prefer": [...]}}
                    if "segmentation.prefer" in rules_result.rules:
                        prefer = rules_result.rules.get("segmentation.prefer", [])
                    elif "segmentation" in rules_result.rules and isinstance(rules_result.rules["segmentation"], dict):
                        prefer = rules_result.rules["segmentation"].get("prefer", ["removebg", "rembg"])
                    else:
                        prefer = ["removebg", "rembg"]  # 默认值
                    
                    if "segmentation.timeoutMs" in rules_result.rules:
                        seg_timeout_ms = rules_result.rules.get("segmentation.timeoutMs", 6000)
                    elif "segmentation" in rules_result.rules and isinstance(rules_result.rules["segmentation"], dict):
                        seg_timeout_ms = rules_result.rules["segmentation"].get("timeoutMs", 6000)
                    else:
                        seg_timeout_ms = 6000  # 默认值
                    
                    # hintParams：至少传 output="rgba"
                    hint_params = {"output": "rgba"}
                    if "segmentation" in rules_result.rules and isinstance(rules_result.rules["segmentation"], dict):
                        seg_config = rules_result.rules["segmentation"]
                        if "output" in seg_config:
                            hint_params["output"] = seg_config["output"]
                        if "quality" in seg_config:
                            hint_params["quality"] = seg_config["quality"]
                    
                    # 调用 platform resolve
                    platform_client = PlatformClient()
                    execution_plan = platform_client.resolve(
                        template_code=req.templateCode,
                        version_semver=req.versionSemver,
                        prefer=prefer,
                        timeout_ms=seg_timeout_ms,
                        hint_params=hint_params,
                    )
                    
                    # 提取 providerCode 和 endpoint（PlatformClient 已经解析好格式）
                    provider_code = execution_plan.get("providerCode", "unknown")
                    endpoint = execution_plan.get("endpoint", "")
                    
                    # 写入 notes
                    notes.append(NoteItem(
                        code="SEG_RESOLVED_PROVIDER",
                        message=f"Platform resolved segmentation provider: {provider_code}",
                        details={
                            "providerCode": provider_code,
                            "endpoint": endpoint,
                        },
                    ))
                except PlatformResolveError as e:
                    # resolve 失败：记录错误，但不崩溃
                    print(f"[process_v2] ⚠️ Platform resolve failed: {e}")
                    notes.append(NoteItem(
                        code="SEG_RESOLVE_FAILED",
                        message="Platform resolve failed, will use fallback",
                        details={
                            "error": str(e),
                            "value": True,
                        },
                    ))
                except Exception as e:
                    # 其他异常：记录错误，但不崩溃
                    print(f"[process_v2] ⚠️ Unexpected error during platform resolve: {e}")
                    notes.append(NoteItem(
                        code="SEG_RESOLVE_FAILED",
                        message="Platform resolve failed with unexpected error",
                        details={
                            "error": str(e),
                            "value": True,
                        },
                    ))
            
            # 从 runtime_spec 提取引擎信息（如果有）
            engine_info = runtime_spec.get("engine") or runtime_spec.get("renderEngine")
            if engine_info:
                notes.append(NoteItem(
                    code="ENGINE",
                    message="Render engine information",
                    details={"engine": engine_info}
                ))
            elif "manifestVersion" in runtime_spec:
                notes.append(NoteItem(
                    code="ENGINE",
                    message="Render engine information",
                    details={"manifestVersion": runtime_spec["manifestVersion"]}
                ))
        except ManifestLoadError as e:
            manifest_load_ms = int((time.time() - manifest_load_start) * 1000)
            timing_steps.append(StepInfo(name="MANIFEST_LOAD", ms=manifest_load_ms))
            return PipelineV2ResponseError(
                ok=False,
                jobId=job_id,
                error={
                    "code": "MANIFEST_LOAD_ERROR",
                    "message": str(e),
                    "detail": {"templateCode": req.templateCode}
                },
                timing=TimingInfo(totalMs=int((time.time() - start_time) * 1000), steps=timing_steps),
                notes=[NoteItem(
                    code="ERROR_MANIFEST_LOAD",
                    message="Failed to load manifest.json",
                    details={"error": str(e)}
                )]
            ).model_dump()
        except ManifestValidationError as e:
            manifest_load_ms = int((time.time() - manifest_load_start) * 1000)
            timing_steps.append(StepInfo(name="MANIFEST_LOAD", ms=manifest_load_ms))
            
            # 打印详细错误信息用于调试
            print(f"[process_v2] ❌ ManifestValidationError caught: {e}")
            print(f"[process_v2] Error type: {type(e)}")
            print(f"[process_v2] Error message: {str(e)}")
            print(f"[process_v2] Template dir: {template_dir if 'template_dir' in locals() else 'N/A'}")
            
            # 根据错误消息判断是资源文件缺失还是 manifest 结构错误
            error_msg = str(e).lower()
            if "not found" in error_msg or "file not found" in error_msg or "background file" in error_msg or "sticker file" in error_msg:
                error_code = "ASSET_NOT_FOUND"
                print(f"[process_v2] Error code: ASSET_NOT_FOUND (asset file missing)")
            else:
                error_code = "MANIFEST_INVALID"
                print(f"[process_v2] Error code: MANIFEST_INVALID (manifest structure/field validation failed)")
            
            return PipelineV2ResponseError(
                ok=False,
                jobId=job_id,
                error={
                    "code": error_code,
                    "message": str(e),
                    "retryable": False,
                    "detail": {"templateCode": req.templateCode}
                },
                timing=TimingInfo(totalMs=int((time.time() - start_time) * 1000), steps=timing_steps),
                notes=[NoteItem(
                    code="ERROR_MANIFEST_VALIDATION",
                    message="Manifest validation failed",
                    details={"error": str(e)}
                )]
            ).model_dump()
        
        # 3. 加载原始图像
        if not req.rawPath:
            return PipelineV2ResponseError(
                ok=False,
                jobId=job_id,
                error={
                    "code": "INVALID_INPUT",
                    "message": "rawPath is required",
                    "detail": {}
                },
                timing=None,
                notes=[NoteItem(
                    code="ERROR_INVALID_REQUEST",
                    message="Missing required field: rawPath",
                    details={}
                )]
            ).model_dump()
        
        raw_path = Path(req.rawPath)
        if not raw_path.exists():
            return PipelineV2ResponseError(
                ok=False,
                jobId=job_id,
                error={
                    "code": "INVALID_INPUT",
                    "message": f"Raw image file not found: {req.rawPath}",
                    "detail": {"rawPath": str(req.rawPath)}
                },
                timing=TimingInfo(totalMs=int((time.time() - start_time) * 1000), steps=timing_steps),
                notes=[NoteItem(
                    code="ERROR_FILE_NOT_FOUND",
                    message="Raw image file does not exist",
                    details={"path": str(req.rawPath)}
                )]
            ).model_dump()
        
        # 4. 加载原始图像
        raw_image = Image.open(raw_path)
        
        # 5. 执行抠图（如果需要）
        cutout_image = None
        artifacts = None
        if needs_segmentation:
            seg_start = time.time()
            try:
                segmentation_service = SegmentationService()
                cutout_image, seg_notes_list = segmentation_service.segment(
                    raw_image=raw_image,
                    template_code=req.templateCode,
                    version_semver=req.versionSemver,
                    rules=rules_result.rules,
                )
                
                # 将 seg_notes 转换为 NoteItem 并添加到 notes
                for seg_note in seg_notes_list:
                    notes.append(NoteItem(
                        code=seg_note.get("code", "SEG_UNKNOWN"),
                        message=seg_note.get("message", ""),
                        details=seg_note.get("details", {})
                    ))
                
                # 如果成功得到 cutout，准备 artifacts
                if cutout_image is not None:
                    artifacts = {"cutout": cutout_image}
                
                seg_ms = int((time.time() - seg_start) * 1000)
                timing_steps.append(StepInfo(name="SEGMENTATION", ms=seg_ms))
            except Exception as e:
                # 抠图失败不应该导致整个请求失败（fallback 应该已经处理）
                seg_ms = int((time.time() - seg_start) * 1000)
                timing_steps.append(StepInfo(name="SEGMENTATION", ms=seg_ms))
                print(f"[process_v2] ⚠️ Segmentation failed (should have fallback): {e}")
                notes.append(NoteItem(
                    code="SEG_ERROR",
                    message=f"Segmentation error: {str(e)[:200]}",
                    details={"error": str(e)[:200]}
                ))
        
        # 6. 渲染图像
        render_start = time.time()
        try:
            render_engine = RenderEngine(runtime_spec)
            final_image = render_engine.render(raw_image, artifacts=artifacts)
            render_ms = int((time.time() - render_start) * 1000)
            timing_steps.append(StepInfo(name="RENDER", ms=render_ms))
        except RenderError as e:
            render_ms = int((time.time() - render_start) * 1000)
            timing_steps.append(StepInfo(name="RENDER", ms=render_ms))
            return PipelineV2ResponseError(
                ok=False,
                jobId=job_id,
                error={
                    "code": "RENDER_FAILED",
                    "message": str(e),
                    "retryable": False,
                    "detail": {"rawPath": str(req.rawPath)}
                },
                timing=TimingInfo(totalMs=int((time.time() - start_time) * 1000), steps=timing_steps),
                notes=[NoteItem(
                    code="ERROR_RENDER_FAILED",
                    message="Image rendering failed",
                    details={"error": str(e)}
                )]
            ).model_dump()
        except Exception as e:
            render_ms = int((time.time() - render_start) * 1000)
            timing_steps.append(StepInfo(name="RENDER", ms=render_ms))
            return PipelineV2ResponseError(
                ok=False,
                jobId=job_id,
                error={
                    "code": "RENDER_FAILED",
                    "message": f"Unexpected error during rendering: {e}",
                    "retryable": False,
                    "detail": {"rawPath": str(req.rawPath)}
                },
                timing=TimingInfo(totalMs=int((time.time() - start_time) * 1000), steps=timing_steps),
                notes=[NoteItem(
                    code="ERROR_RENDER_FAILED",
                    message="Image rendering failed with unexpected error",
                    details={"error": str(e)}
                )]
            ).model_dump()
        
        # 5. 存储图像（preview 暂时复用 final）
        store_start = time.time()
        try:
            storage_manager = StorageManager()
            
            # 存储 final
            final_info = storage_manager.store_final(job_id, final_image, fmt="png")
            final_url = final_info["url"]
            
            # preview 暂时复用 final（根据要求）
            preview_info = storage_manager.store_preview(job_id, final_image, fmt="png")
            preview_url = preview_info["url"]
            
            # 添加 notes：preview 等于 final
            notes.append(NoteItem(
                code="PREVIEW_EQUALS_FINAL",
                message="Preview image is currently using the same image as final (temporary implementation)",
                details={}
            ))
            
            store_ms = int((time.time() - store_start) * 1000)
            timing_steps.append(StepInfo(name="STORE", ms=store_ms))
        except StorageError as e:
            store_ms = int((time.time() - store_start) * 1000)
            timing_steps.append(StepInfo(name="STORE", ms=store_ms))
            return PipelineV2ResponseError(
                ok=False,
                jobId=job_id,
                error={
                    "code": "STORE_FAILED",
                    "message": str(e),
                    "retryable": True,
                    "detail": {"targetPath": str(e.target_path) if e.target_path else None}
                },
                timing=TimingInfo(totalMs=int((time.time() - start_time) * 1000), steps=timing_steps),
                notes=[NoteItem(
                    code="ERROR_STORAGE_FAILED",
                    message="Failed to store rendered image",
                    details={"error": str(e)}
                )]
            ).model_dump()
        
        # 6. 构建成功响应
        total_ms = int((time.time() - start_time) * 1000)
        
        # 确保 URL 是完整的（如果 StorageManager 返回的是相对路径，需要拼接 base_url）
        if preview_url.startswith("/"):
            preview_url = f"{base_url}{preview_url}"
        if final_url.startswith("/"):
            final_url = f"{base_url}{final_url}"
        
        response = PipelineV2ResponseOk(
            ok=True,
            jobId=job_id,
            template=TemplateInfo(
                templateCode=runtime_spec["templateCode"],
                versionSemver=runtime_spec["versionSemver"],
                manifestVersion=runtime_spec.get("manifestVersion", 1)
            ),
            outputs=OutputUrls(
                previewUrl=preview_url,
                finalUrl=final_url
            ),
            timing=TimingInfo(
                totalMs=total_ms,
                steps=timing_steps
            ),
            warnings=warnings,
            notes=notes
        )
        
        return response.model_dump()
        
    except Exception as e:
        # 捕获所有未预期的异常，确保不抛 500
        total_ms = int((time.time() - start_time) * 1000)
        return PipelineV2ResponseError(
            ok=False,
            jobId=job_id,
            error={
                "code": "INTERNAL_ERROR",
                "message": f"Unexpected error: {e}",
                "retryable": False,
                "detail": {}
            },
            timing=TimingInfo(totalMs=total_ms, steps=timing_steps),
            notes=[NoteItem(
                code="ERROR_INTERNAL",
                message="Internal server error",
                details={"error": str(e)}
            )]
        ).model_dump()


# 统一导出的 router：包含 v1 和 v2
router = APIRouter()
router.include_router(router_v1)
router.include_router(router_v2)
