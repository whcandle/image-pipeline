"""
汇总测试（legacy v1）

当前项目已经迁移到基于 manifest/runtime_spec 的 v2 架构，
本文件中的旧版汇总测试仅针对早期的 outputWidth/outputHeight 协议，
与现有实现不再匹配，因此整体跳过。
"""

import pytest

pytestmark = pytest.mark.skip(reason="Legacy v1 pipeline tests (outputWidth/outputHeight); superseded by v2 modules.")
