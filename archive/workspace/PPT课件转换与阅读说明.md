> 历史记录脱敏副本：其中“当前”“已验证”仅指原记录时点；操作路径已替换。公开版以仓库 README 和复现说明为准。

# PPT课件转换与阅读说明

## 现在开始读课件

打开 DeepTutor → 左上角选择 **Computer Programming (Python) · 期末备考** → **学习 → 沉浸式阅读** → **英文原版 PDF 课件 · Computer Programming**。顶部文件名可切换 Lecture01—Lecture06；右侧“伴读”可边看边问，点击回答中的 p.xx 返回原页。窗口较窄时收起侧栏或伴读，宽窗口可并排阅读。

推荐提问：
> 用中文解释当前页，保留英文术语和代码缩进；引用准确页码；先给提示，再出一道英文练习题。

旧 PPT 合集仍叫“原始英文课件 · Computer Programming”。其进度、批注、书签和知识库保留，不会自动迁移到新 PDF。桌面与 CLI/PyPI 各自保存阅读记录，数据仍隔离。

## 以后添加 PPT

工具目录：`C:\Users\YOUR_NAME\Documents\ChatGPT\Academic learning\DeepTutor-conversion-tools`

1. 双击 **PPT转PDF.cmd** 选择 PPT/PPTX，也可将文件拖到脚本上。支持中文、空格路径；相同内容跳过，同名不同内容另存版本，原文件保留。
2. 默认结果在 `C:\Users\YOUR_NAME\Documents\ChatGPT\Academic learning\Course materials\Converted PDFs`。
3. 先打开桌面 DeepTutor，再双击 **导入Python PDF到两套DeepTutor.cmd** 选择结果 PDF，分别追加到两套 Python 合集并去重。CLI/PyPI 原来关闭时会临时启动，完成后恢复关闭。此入口专用于 Python；其他科目请进入对应工作区手动“添加资料”。
4. 阅读导入不会重复建知识库。当前课件沿用 Python-English-Lectures；新章节需要跨资料检索时，再追加到原知识库。

备用 **PDF转图片PPT.cmd**：每页一张图片，不能恢复逐字可编辑文字，不作为首选阅读材料。默认输出：`C:\Users\YOUR_NAME\Documents\ChatGPT\Academic learning\Course materials\Image PPTX backup`。

## 本次结果与限制

六份阅读用 PDF 在 `C:\Users\YOUR_NAME\Documents\ChatGPT\Academic learning\Course materials\Computer Programming\英文原版 PDF 课件`。

页数分别为27、70、53、68、74、82，共374页。已逐页核对文字、比例、空白和字体，查看全部页缩略图，并抽查16个高分辨率代表页。两套真实阅读前端均显示完整页面，完成中文问答并实际点击引用跳页：桌面 Lecture04 p.11、CLI/PyPI Lecture03 p.45。备用两页 PPTX、CMD入口和重复跳过也已验证。

**Lecture02 使用“阅读修正版_仅第65页”**：原第65页有两张卡片放在画布外，仅将该页卡片区域缩小放回；文字不变、其余69页渲染一致。原 PPT 和忠实导出 PDF 保留。Lecture03 包含原来的隐藏第45页，以保持页码一致。

PDF 是静态页面，不保留动画或交互；部分原图文字不可选择，复制代码后需核对缩进。未做全部页面与 PowerPoint 的逐像素对照，也未自动操控 Electron 原生窗口；已验证桌面服务对应的实际阅读前端。默认 GPT-6.1-Sol/high 保持，未新增付费 API、文件关联或自启动。

安装位置（均为工具目录下）：LibreOffice 26.8.2.2 在 `LibreOffice\program`；pdf2pptx 1.0.5 在 `.venv-pdf2pptx\Scripts`，使用独立 `Python310`，未改 DeepTutor 依赖。

完整安装路径、官方来源、合集直达链接和验收细节见工具目录 `verification\操作与验收详记.md`；结构化报告为 `verification\final-verification.json`。
