# 改动与源文件清单

以官方 v1.7.1 commit `f7aed0744c36c5afef16a4261c31ebee1208cac2` 为唯一基线。基线字节哈希与导出源码哈希见 `upstream/manifest.json`。CLI 与桌面后端为替代目标；前端和桌面壳是另外的组件。

## cli

补丁：`patches/cli-v1.7.1.patch`

| 完整公开源码 | 对官方基线 |
|---|---|
| [deeptutor/api/routers/knowledge.py](../overrides/cli/deeptutor/api/routers/knowledge.py) | 修改 |
| [deeptutor/api/routers/reading.py](../overrides/cli/deeptutor/api/routers/reading.py) | 修改 |
| [deeptutor/knowledge/add_documents.py](../overrides/cli/deeptutor/knowledge/add_documents.py) | 修改 |
| [deeptutor/knowledge/initializer.py](../overrides/cli/deeptutor/knowledge/initializer.py) | 修改 |
| [deeptutor/reading/knowledge_sync.py](../overrides/cli/deeptutor/reading/knowledge_sync.py) | 新增 |
| [deeptutor/runtime/launcher.py](../overrides/cli/deeptutor/runtime/launcher.py) | 修改 |
| [deeptutor/services/model_selection/llm.py](../overrides/cli/deeptutor/services/model_selection/llm.py) | 修改 |

## desktop

补丁：`patches/desktop-v1.7.1.patch`

| 完整公开源码 | 对官方基线 |
|---|---|
| [deeptutor/api/routers/knowledge.py](../overrides/desktop/deeptutor/api/routers/knowledge.py) | 修改 |
| [deeptutor/api/routers/reading.py](../overrides/desktop/deeptutor/api/routers/reading.py) | 修改 |
| [deeptutor/capabilities/reading/capability.py](../overrides/desktop/deeptutor/capabilities/reading/capability.py) | 修改 |
| [deeptutor/capabilities/reading/tools.py](../overrides/desktop/deeptutor/capabilities/reading/tools.py) | 修改 |
| [deeptutor/knowledge/add_documents.py](../overrides/desktop/deeptutor/knowledge/add_documents.py) | 修改 |
| [deeptutor/knowledge/initializer.py](../overrides/desktop/deeptutor/knowledge/initializer.py) | 修改 |
| [deeptutor/reading/extract.py](../overrides/desktop/deeptutor/reading/extract.py) | 修改 |
| [deeptutor/reading/knowledge_sync.py](../overrides/desktop/deeptutor/reading/knowledge_sync.py) | 新增 |
| [deeptutor/reading/native_ocr.py](../overrides/desktop/deeptutor/reading/native_ocr.py) | 新增 |
| [deeptutor/reading/store.py](../overrides/desktop/deeptutor/reading/store.py) | 修改 |
| [deeptutor/services/model_selection/llm.py](../overrides/desktop/deeptutor/services/model_selection/llm.py) | 修改 |

## frontend

补丁：`patches/frontend-v1.7.1.patch`

| 完整公开源码 | 对官方基线 |
|---|---|
| [web/components/chat/home/ChatComposer.tsx](../overrides/frontend/web/components/chat/home/ChatComposer.tsx) | 修改 |
| [web/components/chat/home/ModelSelector.tsx](../overrides/frontend/web/components/chat/home/ModelSelector.tsx) | 修改 |
| [web/components/chat/home/ReasoningEffortSelector.tsx](../overrides/frontend/web/components/chat/home/ReasoningEffortSelector.tsx) | 新增 |
| [web/components/reading/workspace/ReadingComposer.tsx](../overrides/frontend/web/components/reading/workspace/ReadingComposer.tsx) | 修改 |
| [web/lib/chat-reasoning.ts](../overrides/frontend/web/lib/chat-reasoning.ts) | 新增 |
| [web/lib/llm-options.ts](../overrides/frontend/web/lib/llm-options.ts) | 修改 |
| [web/tests/chat-reasoning-selector.spec.tsx](../overrides/frontend/web/tests/chat-reasoning-selector.spec.tsx) | 新增 |

## desktop-shell

补丁：`patches/desktop-shell-v1.7.1.patch`

| 完整公开源码 | 对官方基线 |
|---|---|
| [apps/desktop/src/main.mjs](../overrides/desktop-shell/apps/desktop/src/main.mjs) | 修改 |

## 历史脚本与说明

`archive/workspace/` 保留原同级目录关系。下表列出公开副本；实际课程文件、账号数据与原始验证输出不在归档。

| 原相对路径 | 公开副本 |
|---|---|
| `DeepTutor/Codex与桌面版使用说明.md` | [Codex与桌面版使用说明.md](../archive/workspace/DeepTutor/Codex与桌面版使用说明.md) |
| `DeepTutor/DeepSeek账号与推理强度说明.md` | [DeepSeek账号与推理强度说明.md](../archive/workspace/DeepTutor/DeepSeek账号与推理强度说明.md) |
| `DeepTutor/DeepWorks模型接入说明.md` | [DeepWorks模型接入说明.md](../archive/workspace/DeepTutor/DeepWorks模型接入说明.md) |
| `DeepTutor/Login-Codex.cmd` | [Login-Codex.cmd](../archive/workspace/DeepTutor/Login-Codex.cmd) |
| `DeepTutor/requirements-installed.txt` | [requirements-installed.txt](../archive/workspace/DeepTutor/requirements-installed.txt) |
| `DeepTutor/Start-DeepTutor.cmd` | [Start-DeepTutor.cmd](../archive/workspace/DeepTutor/Start-DeepTutor.cmd) |
| `DeepTutor/start_deeptutor.py` | [start_deeptutor.py](../archive/workspace/DeepTutor/start_deeptutor.py) |
| `DeepTutor/Stop-DeepTutor.cmd` | [Stop-DeepTutor.cmd](../archive/workspace/DeepTutor/Stop-DeepTutor.cmd) |
| `DeepTutor/stop_deeptutor.py` | [stop_deeptutor.py](../archive/workspace/DeepTutor/stop_deeptutor.py) |
| `DeepTutor/使用说明.md` | [使用说明.md](../archive/workspace/DeepTutor/使用说明.md) |
| `DeepTutor/安装验证记录.md` | [安装验证记录.md](../archive/workspace/DeepTutor/安装验证记录.md) |
| `DeepTutor/整体检查记录.md` | [整体检查记录.md](../archive/workspace/DeepTutor/整体检查记录.md) |
| `DeepTutor-learning-support/configure_learning_services.py` | [configure_learning_services.py](../archive/workspace/DeepTutor-learning-support/configure_learning_services.py) |
| `DeepTutor-learning-support/ensure_support.py` | [ensure_support.py](../archive/workspace/DeepTutor-learning-support/ensure_support.py) |
| `DeepTutor-learning-support/finalize_course_indexes.py` | [finalize_course_indexes.py](../archive/workspace/DeepTutor-learning-support/finalize_course_indexes.py) |
| `DeepTutor-learning-support/import_course_materials.py` | [import_course_materials.py](../archive/workspace/DeepTutor-learning-support/import_course_materials.py) |
| `DeepTutor-learning-support/launch_desktop.py` | [launch_desktop.py](../archive/workspace/DeepTutor-learning-support/launch_desktop.py) |
| `DeepTutor-learning-support/requirements.lock.txt` | [requirements.lock.txt](../archive/workspace/DeepTutor-learning-support/requirements.lock.txt) |
| `DeepTutor-learning-support/server.py` | [server.py](../archive/workspace/DeepTutor-learning-support/server.py) |
| `DeepTutor-conversion-tools/audit_pdf_output.py` | [audit_pdf_output.py](../archive/workspace/DeepTutor-conversion-tools/audit_pdf_output.py) |
| `DeepTutor-conversion-tools/convert_materials.py` | [convert_materials.py](../archive/workspace/DeepTutor-conversion-tools/convert_materials.py) |
| `DeepTutor-conversion-tools/finalize_pdf_collections.py` | [finalize_pdf_collections.py](../archive/workspace/DeepTutor-conversion-tools/finalize_pdf_collections.py) |
| `DeepTutor-conversion-tools/import_python_pdfs.py` | [import_python_pdfs.py](../archive/workspace/DeepTutor-conversion-tools/import_python_pdfs.py) |
| `DeepTutor-conversion-tools/PDF教材自动处理与导入.cmd` | [PDF教材自动处理与导入.cmd](../archive/workspace/DeepTutor-conversion-tools/PDF教材自动处理与导入.cmd) |
| `DeepTutor-conversion-tools/PDF转图片PPT.cmd` | [PDF转图片PPT.cmd](../archive/workspace/DeepTutor-conversion-tools/PDF转图片PPT.cmd) |
| `DeepTutor-conversion-tools/PPT转PDF.cmd` | [PPT转PDF.cmd](../archive/workspace/DeepTutor-conversion-tools/PPT转PDF.cmd) |
| `DeepTutor-conversion-tools/repair_lecture02_overflow.py` | [repair_lecture02_overflow.py](../archive/workspace/DeepTutor-conversion-tools/repair_lecture02_overflow.py) |
| `DeepTutor-conversion-tools/requirements-pdf2pptx.lock.txt` | [requirements-pdf2pptx.lock.txt](../archive/workspace/DeepTutor-conversion-tools/requirements-pdf2pptx.lock.txt) |
| `DeepTutor-conversion-tools/verify_final_setup.py` | [verify_final_setup.py](../archive/workspace/DeepTutor-conversion-tools/verify_final_setup.py) |
| `DeepTutor-conversion-tools/导入Python PDF到两套DeepTutor.cmd` | [导入Python PDF到两套DeepTutor.cmd](../archive/workspace/DeepTutor-conversion-tools/导入Python%20PDF到两套DeepTutor.cmd) |
| `DeepTutor-conversion-tools/ocr/download_models.py` | [download_models.py](../archive/workspace/DeepTutor-conversion-tools/ocr/download_models.py) |
| `DeepTutor-conversion-tools/ocr/import_searchable.py` | [import_searchable.py](../archive/workspace/DeepTutor-conversion-tools/ocr/import_searchable.py) |
| `DeepTutor-conversion-tools/ocr/inspect_calculus.py` | [inspect_calculus.py](../archive/workspace/DeepTutor-conversion-tools/ocr/inspect_calculus.py) |
| `DeepTutor-conversion-tools/ocr/inspect_reading.py` | [inspect_reading.py](../archive/workspace/DeepTutor-conversion-tools/ocr/inspect_reading.py) |
| `DeepTutor-conversion-tools/ocr/make_searchable.py` | [make_searchable.py](../archive/workspace/DeepTutor-conversion-tools/ocr/make_searchable.py) |
| `DeepTutor-conversion-tools/ocr/make_searchable_rapid.py` | [make_searchable_rapid.py](../archive/workspace/DeepTutor-conversion-tools/ocr/make_searchable_rapid.py) |
| `DeepTutor-conversion-tools/ocr/validate_searchable.py` | [validate_searchable.py](../archive/workspace/DeepTutor-conversion-tools/ocr/validate_searchable.py) |
| `DeepTutor-conversion-tools/ocr/write_delivery_note.py` | [write_delivery_note.py](../archive/workspace/DeepTutor-conversion-tools/ocr/write_delivery_note.py) |
| `DeepTutor-conversion-tools/pdf-textbook-tool/adopt_current_book.py` | [adopt_current_book.py](../archive/workspace/DeepTutor-conversion-tools/pdf-textbook-tool/adopt_current_book.py) |
| `DeepTutor-conversion-tools/pdf-textbook-tool/cli.py` | [cli.py](../archive/workspace/DeepTutor-conversion-tools/pdf-textbook-tool/cli.py) |
| `DeepTutor-conversion-tools/pdf-textbook-tool/deeptutor_client.py` | [deeptutor_client.py](../archive/workspace/DeepTutor-conversion-tools/pdf-textbook-tool/deeptutor_client.py) |
| `DeepTutor-conversion-tools/pdf-textbook-tool/engine.py` | [engine.py](../archive/workspace/DeepTutor-conversion-tools/pdf-textbook-tool/engine.py) |
| `DeepTutor-conversion-tools/pdf-textbook-tool/gui.py` | [gui.py](../archive/workspace/DeepTutor-conversion-tools/pdf-textbook-tool/gui.py) |
| `DeepTutor-conversion-tools/pdf-textbook-tool/pipeline.py` | [pipeline.py](../archive/workspace/DeepTutor-conversion-tools/pdf-textbook-tool/pipeline.py) |
| `DeepTutor-conversion-tools/pdf-textbook-tool/verify_import.py` | [verify_import.py](../archive/workspace/DeepTutor-conversion-tools/pdf-textbook-tool/verify_import.py) |
| `DeepTutor-conversion-tools/pdf-textbook-tool/verify_tool.py` | [verify_tool.py](../archive/workspace/DeepTutor-conversion-tools/pdf-textbook-tool/verify_tool.py) |
| `DeepTutor-conversion-tools/pdf-textbook-tool/使用说明.md` | [使用说明.md](../archive/workspace/DeepTutor-conversion-tools/pdf-textbook-tool/使用说明.md) |
| `DeepTutor-native-ocr/deploy.py` | [deploy.py](../archive/workspace/DeepTutor-native-ocr/deploy.py) |
| `DeepTutor-native-ocr/finish_audit.py` | [finish_audit.py](../archive/workspace/DeepTutor-native-ocr/finish_audit.py) |
| `DeepTutor-native-ocr/fix_desktop_layout.py` | [fix_desktop_layout.py](../archive/workspace/DeepTutor-native-ocr/fix_desktop_layout.py) |
| `DeepTutor-native-ocr/prepare_ui.py` | [prepare_ui.py](../archive/workspace/DeepTutor-native-ocr/prepare_ui.py) |
| `DeepTutor-native-ocr/test_failure.py` | [test_failure.py](../archive/workspace/DeepTutor-native-ocr/test_failure.py) |
| `DeepTutor-native-ocr/test_native.py` | [test_native.py](../archive/workspace/DeepTutor-native-ocr/test_native.py) |
| `DeepTutor-native-ocr/verify_live.py` | [verify_live.py](../archive/workspace/DeepTutor-native-ocr/verify_live.py) |
| `DeepTutor-native-ocr/worker.py` | [worker.py](../archive/workspace/DeepTutor-native-ocr/worker.py) |
| `DeepTutor-native-ocr/使用说明与验证记录.md` | [使用说明与验证记录.md](../archive/workspace/DeepTutor-native-ocr/使用说明与验证记录.md) |
| `DeepTutor-knowledge-reading-sync/backfill.py` | [backfill.py](../archive/workspace/DeepTutor-knowledge-reading-sync/backfill.py) |
| `DeepTutor-knowledge-reading-sync/baseline.py` | [baseline.py](../archive/workspace/DeepTutor-knowledge-reading-sync/baseline.py) |
| `DeepTutor-knowledge-reading-sync/prepare.py` | [prepare.py](../archive/workspace/DeepTutor-knowledge-reading-sync/prepare.py) |
| `DeepTutor-knowledge-reading-sync/test_sync.py` | [test_sync.py](../archive/workspace/DeepTutor-knowledge-reading-sync/test_sync.py) |
| `DeepTutor-knowledge-reading-sync/verify_preservation.py` | [verify_preservation.py](../archive/workspace/DeepTutor-knowledge-reading-sync/verify_preservation.py) |
| `DeepTutor-knowledge-reading-sync/verify_upload_flow.py` | [verify_upload_flow.py](../archive/workspace/DeepTutor-knowledge-reading-sync/verify_upload_flow.py) |
| `DeepTutor-knowledge-reading-sync/同步说明.md` | [同步说明.md](../archive/workspace/DeepTutor-knowledge-reading-sync/同步说明.md) |
| `DeepTutor-menu-placement/deploy_frontend.py` | [deploy_frontend.py](../archive/workspace/DeepTutor-menu-placement/deploy_frontend.py) |
| `DeepTutor-menu-placement/修复说明.md` | [修复说明.md](../archive/workspace/DeepTutor-menu-placement/修复说明.md) |
| `PPT课件转换与阅读说明.md` | [PPT课件转换与阅读说明.md](../archive/workspace/PPT课件转换与阅读说明.md) |
| `DeepTutor-knowledge-reading-sync/patch/knowledge_sync.py` | [knowledge_sync.py](../archive/workspace/DeepTutor-knowledge-reading-sync/patch/knowledge_sync.py) |
| `DeepTutor/sync_deepseek_account.py` | [sync_deepseek_account.py](../archive/workspace/DeepTutor/sync_deepseek_account.py) |

另有发布时新增的 `tools/`、`tests/`、`examples/` 和整理文档。原 DeepWorks 凭据自动提取代码不在上述文件中。
