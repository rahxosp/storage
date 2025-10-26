"""Metrics Viewer dialog with Matplotlib graph for CPU/GPU usage."""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import List, Tuple
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from metrics_db import fetch_series


class MetricsViewerDialog:
    def __init__(self, parent, server_name: str):
        self.parent = parent
        self.server_name = server_name
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Metrics - {server_name}")
        self.dialog.geometry("900x500")
        
        self.metric_var = tk.StringVar(value="cpu")
        self.seconds_var = tk.IntVar(value=300)  # last 5 minutes
        
        self._create_widgets()
        self._init_plot()
        
        # periodic refresh
        self._schedule_update()
        
        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        toolbar = ttk.Frame(self.dialog)
        toolbar.pack(fill=tk.X, padx=6, pady=6)
        
        ttk.Label(toolbar, text="Metric:").pack(side=tk.LEFT)
        metric_cb = ttk.Combobox(toolbar, textvariable=self.metric_var, values=["cpu", "gpu_util", "ram_used_mb", "gpu_mem_used_mb"], width=20, state='readonly')
        metric_cb.pack(side=tk.LEFT, padx=6)
        metric_cb.bind('<<ComboboxSelected>>', lambda e: self._refresh_plot())
        
        ttk.Label(toolbar, text="Window (s):").pack(side=tk.LEFT, padx=(10,0))
        win_cb = ttk.Combobox(toolbar, textvariable=self.seconds_var, values=[60, 120, 300, 600, 1800], width=10, state='readonly')
        win_cb.pack(side=tk.LEFT, padx=6)
        win_cb.bind('<<ComboboxSelected>>', lambda e: self._refresh_plot())
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(toolbar, textvariable=self.status_var).pack(side=tk.RIGHT)
        
        # Plot area
        self.figure = Figure(figsize=(7, 3.5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.dialog)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
    
    def _init_plot(self):
        self.ax.clear()
        self.ax.set_title(f"{self.server_name} - {self.metric_var.get()}")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel(self.metric_var.get())
        self.canvas.draw_idle()
    
    def _refresh_plot(self):
        metric = self.metric_var.get()
        seconds = int(self.seconds_var.get())
        data: List[Tuple[int, float]] = fetch_series(self.server_name, metric, seconds=seconds)
        
        self.ax.clear()
        if data:
            xs = [datetime.fromtimestamp(ts) for ts, _ in data]
            ys = [val for _, val in data]
            self.ax.plot(xs, ys, color='tab:blue', linewidth=1.5)
            # Rolling window: always show last N seconds ending at now
            now = datetime.now()
            start = datetime.fromtimestamp(datetime.now().timestamp() - seconds)
            self.ax.set_xlim(start, now)
        self.ax.set_title(f"{self.server_name} - {metric}")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel(metric)
        self.ax.grid(True, linestyle='--', alpha=0.3)
        self.figure.autofmt_xdate()
        self.canvas.draw_idle()
        
        self.status_var.set(f"Points: {len(data)}")
    
    def _schedule_update(self):
        if not self.dialog.winfo_exists():
            return
        self._refresh_plot()
        self.dialog.after(1000, self._schedule_update)
