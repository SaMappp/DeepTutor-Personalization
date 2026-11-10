# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Native Chinese desktop entry point; no server startup, settings changes or paid APIs."""
from pathlib import Path
import json
import multiprocessing
import os
import queue
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
from pipeline import (process_pdf, DEFAULT_OUTPUT, ROOT, Paused, atomic_json)
from deeptutor_client import DeepTutorClient, DESKTOP, CLI

SETTINGS = ROOT / 'tool-settings.json'


class Application:
    def __init__(self, root):
        self.root = root
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.busy = False
        self.closing = False
        self.files = []
        self.workspaces = []
        self.collections = []
        self.last_outputs = []
        self.last_url = ''
        try:
            self.saved = json.loads(SETTINGS.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            self.saved = {}
        root.title('PDF 教材自动处理与导入')
        root.geometry('1080x800')
        root.minsize(900, 700)
        root.option_add('*Font', ('Microsoft YaHei UI', 10))
        style = ttk.Style(root)
        if 'vista' in style.theme_names():
            style.theme_use('vista')
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 17, 'bold'))
        style.configure('Note.TLabel', foreground='#525965')
        panel = ttk.Frame(root, padding=20)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='PDF 教材自动处理与导入', style='Title.TLabel').pack(anchor='w')
        ttk.Label(panel, text='原件保留 · 中文 OCR 在本机运行 · 公式原图保留', style='Note.TLabel').pack(anchor='w', pady=(6, 16))
        source = ttk.LabelFrame(panel, text='1  选择教材', padding=10)
        source.pack(fill='x')
        self.listbox = tk.Listbox(source, height=4, selectmode='extended', font=('Microsoft YaHei UI', 9))
        self.listbox.pack(side='left', fill='both', expand=True)
        buttons = ttk.Frame(source)
        buttons.pack(side='right', padx=(12, 0))
        self.add_button = ttk.Button(buttons, text='添加 PDF…', command=self.add_files)
        self.add_button.pack(fill='x', pady=(0, 6))
        self.remove_button = ttk.Button(buttons, text='移除所选', command=self.remove_files)
        self.remove_button.pack(fill='x')
        opts = ttk.Frame(panel)
        opts.pack(fill='x', pady=10)
        ttk.Label(opts, text='PDF 物理页码：').pack(side='left')
        self.page_range = tk.StringVar()
        self.range_entry = ttk.Entry(opts, textvariable=self.page_range, width=24)
        self.range_entry.pack(side='left')
        ttk.Label(opts, text='留空处理全书；例 1-10,15。与书内印刷页码可能不同。', style='Note.TLabel').pack(side='left', padx=10)
        targets = ttk.LabelFrame(panel, text='2  选择已有 DeepTutor 工作区与阅读组', padding=10)
        targets.pack(fill='x')
        targets.columnconfigure(1, weight=1)
        ttk.Label(targets, text='服务：').grid(row=0, column=0, sticky='w', pady=4)
        self.target = tk.StringVar(value='桌面版（当前使用）')
        self.target_box = ttk.Combobox(targets, textvariable=self.target,
                                      values=['桌面版（当前使用）', 'CLI / PyPI（仅连接已启动服务）'], state='readonly')
        self.target_box.grid(row=0, column=1, sticky='ew', padx=8)
        self.target_box.bind('<<ComboboxSelected>>', lambda e:self.connect())
        self.connect_button = ttk.Button(targets, text='连接 / 刷新列表', command=self.connect)
        self.connect_button.grid(row=0, column=2)
        ttk.Label(targets, text='工作区：').grid(row=1, column=0, sticky='w', pady=4)
        self.workspace_box = ttk.Combobox(targets, state='readonly')
        self.workspace_box.grid(row=1, column=1, columnspan=2, sticky='ew', padx=8)
        self.workspace_box.bind('<<ComboboxSelected>>', lambda e:self.load_collections())
        ttk.Label(targets, text='阅读组：').grid(row=2, column=0, sticky='w', pady=4)
        self.collection_box = ttk.Combobox(targets, state='readonly')
        self.collection_box.grid(row=2, column=1, columnspan=2, sticky='ew', padx=8)
        self.connection_status = tk.StringVar(value='正在连接桌面版……')
        ttk.Label(targets, textvariable=self.connection_status, style='Note.TLabel').grid(row=3, column=0, columnspan=3, sticky='w', pady=(8, 0))
        destination = ttk.Frame(panel)
        destination.pack(fill='x', pady=10)
        ttk.Label(destination, text='输出位置：').pack(side='left')
        self.output_root = tk.StringVar(value=self.saved.get('output_root', str(DEFAULT_OUTPUT)))
        self.output_entry = ttk.Entry(destination, textvariable=self.output_root)
        self.output_entry.pack(side='left', fill='x', expand=True)
        self.choose_output_button = ttk.Button(destination, text='更改…', command=self.choose_output)
        self.choose_output_button.pack(side='right', padx=(8,0))
        note = ('公式、上下标和手写批注的 OCR 可能有误，请按原图核对。\n'
                '部分范围会在输出名称和说明中标明；失败页/暂停任务可再次开始，已完成页面不会重跑。')
        ttk.Label(panel, text=note, style='Note.TLabel', wraplength=980).pack(anchor='w', pady=(0,10))
        action = ttk.Frame(panel)
        action.pack(fill='x')
        self.start_button = ttk.Button(action, text='开始处理并导入', command=self.start)
        self.start_button.pack(side='left')
        self.pause_button = ttk.Button(action, text='完成当前页后暂停', command=self.pause, state='disabled')
        self.pause_button.pack(side='left', padx=8)
        self.open_button = ttk.Button(action, text='打开输出目录', command=self.open_output)
        self.open_button.pack(side='right')
        self.read_button = ttk.Button(action, text='打开阅读组', command=lambda:webbrowser.open(self.last_url), state='disabled')
        self.read_button.pack(side='right', padx=8)
        self.progress = ttk.Progressbar(panel, mode='determinate')
        self.progress.pack(fill='x', pady=(12,4))
        self.status = tk.StringVar(value='准备就绪；首次处理较慢，再次运行会自动复用缓存。')
        ttk.Label(panel, textvariable=self.status).pack(anchor='w')
        self.log_box = tk.Text(panel, height=10, wrap='word', font=('Microsoft YaHei UI', 9), state='disabled')
        self.log_box.pack(fill='both', expand=True, pady=(8,0))
        self.controls = [self.add_button, self.remove_button, self.range_entry, self.target_box,
                         self.connect_button, self.workspace_box, self.collection_box,
                         self.output_entry, self.choose_output_button, self.start_button]
        root.protocol('WM_DELETE_WINDOW', self.on_close)
        root.after(100, self.consume)
        root.after(200, self.connect)

    def base(self):
        return CLI if self.target.get().startswith('CLI') else DESKTOP

    def log(self, text):
        self.log_box.configure(state='normal')
        self.log_box.insert('end', str(text) + '\n')
        self.log_box.see('end'); self.log_box.configure(state='disabled')

    def background(self, function):
        threading.Thread(target=function, daemon=True).start()

    def connect(self):
        if self.busy:
            return
        base = self.base()
        self.workspaces = []; self.collections = []
        self.workspace_box.set(''); self.collection_box.set('')
        self.workspace_box['values'] = []; self.collection_box['values'] = []
        self.connection_status.set('正在连接现有服务……')
        def work():
            client = DeepTutorClient(base)
            try:
                self.events.put(('workspaces', base, client.workspaces()))
            except Exception as exc:
                self.events.put(('connection_error', base, str(exc)))
            finally:
                client.close()
        self.background(work)

    def load_collections(self):
        index = self.workspace_box.current()
        if index < 0 or not self.workspaces:
            return
        workspace = self.workspaces[index]['workspace_id']; base = self.base()
        self.collections = []; self.collection_box.set(''); self.collection_box['values'] = []
        def work():
            client = DeepTutorClient(base)
            try:
                self.events.put(('collections', base, workspace, client.collections(workspace)))
            except Exception as exc:
                self.events.put(('connection_error', base, str(exc)))
            finally:
                client.close()
        self.background(work)

    def add_files(self):
        for name in filedialog.askopenfilenames(title='选择一个或多个 PDF 教材', filetypes=[('PDF 文件','*.pdf')]):
            path = str(Path(name).resolve())
            if path not in self.files:
                self.files.append(path); self.listbox.insert('end', path)

    def remove_files(self):
        for index in reversed(self.listbox.curselection()):
            self.files.pop(index); self.listbox.delete(index)

    def choose_output(self):
        path = filedialog.askdirectory(title='选择输出目录', initialdir=self.output_root.get())
        if path:
            self.output_root.set(path)

    def set_busy(self, value):
        self.busy = value
        for control in self.controls:
            control.configure(state='disabled' if value else ('readonly' if isinstance(control, ttk.Combobox) else 'normal'))
        self.pause_button.configure(state='normal' if value else 'disabled')

    def start(self):
        wi = self.workspace_box.current(); ci = self.collection_box.current()
        if not self.files:
            messagebox.showinfo('请选择教材', '先添加一个或多个 PDF 文件。'); return
        if wi < 0 or ci < 0:
            messagebox.showinfo('请选择导入位置', '请连接现有 DeepTutor，并选择工作区和阅读组。工具不会自动创建或启动服务。'); return
        workspace = self.workspaces[wi]['workspace_id']; collection = self.collections[ci]['workspace_id']
        base = self.base(); files = list(self.files); expression = self.page_range.get(); output = self.output_root.get()
        self.saved = {'output_root': output, 'workspace_id': workspace, 'collection_id': collection}
        atomic_json(SETTINGS, self.saved)
        self.stop.clear(); self.set_busy(True)
        self.status.set('开始处理……'); self.progress['value'] = 0
        def work():
            completed = 0; failed = 0
            client = DeepTutorClient(base)
            try:
                for file in files:
                    if self.stop.is_set():
                        break
                    self.events.put(('log', '开始：' + file))
                    try:
                        result = process_pdf(file, expression, output_root=output,
                            log=lambda text:self.events.put(('log',text)),
                            progress=lambda done,total:self.events.put(('progress',done,total)), stop=self.stop)
                        if self.stop.is_set():
                            break
                        record = client.import_pdf(result, workspace, collection,
                            log=lambda text:self.events.put(('log',text)))
                        completed += 1
                        self.events.put(('result',result['output'],record['url']))
                    except Paused as exc:
                        self.events.put(('log',str(exc))); break
                    except Exception as exc:
                        failed += 1
                        self.events.put(('log','失败：' + str(exc)))
                        logdir = ROOT / 'logs'; logdir.mkdir(exist_ok=True)
                        with (logdir/'errors.log').open('a',encoding='utf-8') as stream:
                            stream.write('\n' + file + '\n' + traceback.format_exc())
                self.events.put(('finished',completed,failed,self.stop.is_set()))
            finally:
                client.close()
        self.background(work)

    def pause(self):
        self.stop.set(); self.pause_button.configure(state='disabled')
        self.status.set('正在完成已开始的页面并保存缓存，随后暂停……')

    def open_output(self):
        path = Path(self.last_outputs[-1]).parent if self.last_outputs else Path(self.output_root.get())
        path.mkdir(parents=True, exist_ok=True); os.startfile(path)

    def consume(self):
        try:
            while True:
                event = self.events.get_nowait(); kind = event[0]
                if kind == 'log':
                    self.log(event[1])
                elif kind == 'workspaces' and event[1] == self.base():
                    self.workspaces = event[2]
                    self.workspace_box['values'] = [w.get('display_name',w['workspace_id']) for w in self.workspaces]
                    if self.workspaces:
                        wanted = self.saved.get('workspace_id')
                        idx = next((i for i,w in enumerate(self.workspaces) if w['workspace_id']==wanted), 0)
                        self.workspace_box.current(idx); self.load_collections()
                    self.connection_status.set('已连接现有服务；未修改 DeepTutor 模型、工作区或服务配置。')
                elif kind == 'collections' and event[1] == self.base():
                    wi = self.workspace_box.current()
                    if wi >= 0 and self.workspaces[wi]['workspace_id'] == event[2]:
                        self.collections = event[3]
                        self.collection_box['values'] = [c['title'] for c in self.collections]
                        if self.collections:
                            wanted = self.saved.get('collection_id')
                            idx = next((i for i,c in enumerate(self.collections) if c['workspace_id']==wanted),0)
                            self.collection_box.current(idx)
                        else:
                            self.connection_status.set('该工作区还没有阅读组，请先在 DeepTutor 中创建，再刷新列表。')
                elif kind == 'connection_error' and event[1] == self.base():
                    self.connection_status.set(event[2]); self.log(event[2])
                elif kind == 'progress':
                    self.progress['maximum'] = event[2]; self.progress['value'] = event[1]
                    self.status.set(f'当前文件：已完成 {event[1]} / {event[2]} 个所选页面')
                elif kind == 'result':
                    self.last_outputs.append(event[1]); self.last_url = event[2]
                    self.read_button.configure(state='normal')
                elif kind == 'finished':
                    self.set_busy(False)
                    self.status.set(('已暂停，缓存已保存。' if event[3] else '处理结束。') + f' 成功导入 {event[1]} 个文件，失败 {event[2]} 个。')
                    if self.closing:
                        self.root.destroy(); return
        except queue.Empty:
            pass
        self.root.after(100, self.consume)

    def on_close(self):
        if self.busy:
            self.closing = True; self.pause()
            self.log('窗口将在当前页保存后关闭；可重新启动继续。')
        else:
            self.root.destroy()


def main():
    multiprocessing.freeze_support()
    root = tk.Tk(); Application(root); root.mainloop()


if __name__ == '__main__':
    main()
