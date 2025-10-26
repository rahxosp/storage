"""Main application - Server Manager GUI with tile cards and metrics."""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
from collections import deque
from manager import ServerManager
from models import ServerStatus
from ui.server_form import ServerFormDialog
from ui.log_viewer import LogViewerDialog
from ui.metrics_viewer import MetricsViewerDialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class ServerTile(ttk.Frame):
    """A single server tile/card widget showing status and metrics."""
    
    def __init__(self, parent, server_name, on_click):
        super().__init__(parent, relief=tk.RAISED, borderwidth=2, padding=10)
        self.server_name = server_name
        self.on_click = on_click
        self.selected = False
        
        # Historical data for sparklines (last 60 data points)
        self.cpu_history = deque(maxlen=60)
        self.gpu_history = deque(maxlen=60)
        
        # Title row
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X)
        
        self.name_label = ttk.Label(title_frame, text=server_name, font=("Arial", 11, "bold"))
        self.name_label.pack(side=tk.LEFT)
        
        self.status_label = ttk.Label(title_frame, text="● Disconnected", font=("Arial", 10))
        self.status_label.pack(side=tk.RIGHT)
        
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # Info section
        self.address_label = ttk.Label(self, text="", font=("Arial", 9))
        self.address_label.pack(anchor=tk.W)
        
        self.pid_label = ttk.Label(self, text="PID: -", font=("Arial", 9))
        self.pid_label.pack(anchor=tk.W)
        
        self.uptime_label = ttk.Label(self, text="Uptime: -", font=("Arial", 9))
        self.uptime_label.pack(anchor=tk.W)
        
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # Metrics section
        metrics_label = ttk.Label(self, text="System Metrics", font=("Arial", 9, "bold"))
        metrics_label.pack(anchor=tk.W)
        
        self.cpu_label = ttk.Label(self, text="CPU: -", font=("Arial", 8))
        self.cpu_label.pack(anchor=tk.W)
        
        self.ram_label = ttk.Label(self, text="RAM: -", font=("Arial", 8))
        self.ram_label.pack(anchor=tk.W)
        
        self.gpu_label = ttk.Label(self, text="GPU: -", font=("Arial", 8))
        self.gpu_label.pack(anchor=tk.W)
        
        self.gpu_mem_label = ttk.Label(self, text="GPU Mem: -", font=("Arial", 8))
        self.gpu_mem_label.pack(anchor=tk.W)
        
        # Mini sparkline graphs
        sparkline_frame = ttk.Frame(self)
        sparkline_frame.pack(fill=tk.X, pady=5)
        
        # CPU sparkline
        self.cpu_figure = Figure(figsize=(1.5, 0.4), dpi=50, facecolor='white')
        self.cpu_ax = self.cpu_figure.add_subplot(111)
        self.cpu_ax.axis('off')
        self.cpu_canvas = FigureCanvasTkAgg(self.cpu_figure, master=sparkline_frame)
        self.cpu_canvas.get_tk_widget().pack(side=tk.LEFT, padx=5)
        
        # GPU sparkline
        self.gpu_figure = Figure(figsize=(1.5, 0.4), dpi=50, facecolor='white')
        self.gpu_ax = self.gpu_figure.add_subplot(111)
        self.gpu_ax.axis('off')
        self.gpu_canvas = FigureCanvasTkAgg(self.gpu_figure, master=sparkline_frame)
        self.gpu_canvas.get_tk_widget().pack(side=tk.LEFT, padx=5)
        
        ttk.Label(sparkline_frame, text="[CPU trend]", font=("Arial", 7)).pack(side=tk.LEFT)
        ttk.Label(sparkline_frame, text="[GPU trend]", font=("Arial", 7)).pack(side=tk.LEFT, padx=5)
        
        # Bind click events
        self.bind("<Button-1>", lambda e: on_click(server_name))
        for child in self.winfo_children():
            child.bind("<Button-1>", lambda e, name=server_name: on_click(name))
            for subchild in child.winfo_children():
                subchild.bind("<Button-1>", lambda e, name=server_name: on_click(name))
        
        # Right-click context menu
        self.bind("<Button-3>", lambda e: on_click(server_name, context_menu=True, event=e))
    
    def update_state(self, config, state):
        """Update tile with server state."""
        self.address_label.config(text=f"📍 {config.get_display_address()}")
        self.pid_label.config(text=f"PID: {state.pid or '-'}")
        
        uptime = self._format_uptime(state.uptime_seconds)
        self.uptime_label.config(text=f"⏱ {uptime}  |  Restarts: {state.restarts_count}")
        
        # Status with color
        status_colors = {
            ServerStatus.RUNNING: "green",
            ServerStatus.STOPPED: "gray",
            ServerStatus.ERROR: "red",
            ServerStatus.DISCONNECTED: "red",
            ServerStatus.CONNECTING: "red",
            ServerStatus.EXTERNAL: "black"
        }
        color = status_colors.get(state.status, "gray")
        self.status_label.config(text=f"● {state.status.value}", foreground=color)
        
        # Color-coded border based on status
        if not self.selected:
            if state.status == ServerStatus.RUNNING:
                self.config(relief=tk.RAISED, borderwidth=2, style='Running.TFrame')
                # Use green-ish background hint
                self.config(padding=10)
            elif state.status == ServerStatus.ERROR:
                self.config(relief=tk.RAISED, borderwidth=3)
                # Thicker border for errors to draw attention
            else:
                self.config(relief=tk.RAISED, borderwidth=2)
    
    def update_metrics(self, metrics):
        """Update tile with metrics data."""
        self.metrics = metrics  # Store for summary calculations
        
        # CPU with alert threshold (>90%)
        cpu = metrics.get('cpu')
        if cpu is not None:
            color = "red" if cpu > 90 else "black"
            self.cpu_label.config(text=f"CPU: {cpu:.1f}%" + (" ⚠️" if cpu > 90 else ""), foreground=color)
        else:
            self.cpu_label.config(text="CPU: -", foreground="black")
        
        # RAM with alert threshold (>90%)
        ram_used = metrics.get('ram_used_mb')
        ram_total = metrics.get('ram_total_mb')
        if ram_used is not None and ram_total is not None:
            pct = 100 * ram_used / ram_total
            color = "red" if pct > 90 else "black"
            self.ram_label.config(text=f"RAM: {ram_used:.0f}/{ram_total:.0f} MB ({pct:.1f}%)" + (" ⚠️" if pct > 90 else ""), foreground=color)
        else:
            self.ram_label.config(text="RAM: -", foreground="black")
        
        # GPU with alert threshold (>95%)
        gpu_util = metrics.get('gpu_util')
        if gpu_util is not None:
            color = "red" if gpu_util > 95 else "black"
            self.gpu_label.config(text=f"GPU: {gpu_util:.1f}%" + (" ⚠️" if gpu_util > 95 else ""), foreground=color)
        else:
            self.gpu_label.config(text="GPU: -", foreground="black")
        
        # GPU Mem with alert threshold (>95%)
        gpu_mem_used = metrics.get('gpu_mem_used_mb')
        gpu_mem_total = metrics.get('gpu_mem_total_mb')
        if gpu_mem_used is not None and gpu_mem_total is not None:
            pct = 100 * gpu_mem_used / gpu_mem_total
            color = "red" if pct > 95 else "black"
            self.gpu_mem_label.config(text=f"GPU Mem: {gpu_mem_used:.0f}/{gpu_mem_total:.0f} MB ({pct:.1f}%)" + (" ⚠️" if pct > 95 else ""), foreground=color)
        else:
            self.gpu_mem_label.config(text="GPU Mem: -", foreground="black")
        
        # Update sparklines
        if cpu is not None:
            self.cpu_history.append(cpu)
        if gpu_util is not None:
            self.gpu_history.append(gpu_util)
        
        self._update_sparklines()
    
    def mark_selected(self, selected: bool):
        """Mark tile as selected or not."""
        self.selected = selected
        if selected:
            self.config(relief=tk.SOLID, borderwidth=3)
        else:
            self.config(relief=tk.RAISED, borderwidth=2)
    
    def _update_sparklines(self):
        """Update mini sparkline graphs."""
        # CPU sparkline
        self.cpu_ax.clear()
        self.cpu_ax.axis('off')
        if len(self.cpu_history) > 1:
            self.cpu_ax.plot(list(self.cpu_history), color='tab:blue', linewidth=1)
            self.cpu_ax.set_ylim(0, 100)
        self.cpu_figure.tight_layout(pad=0)
        self.cpu_canvas.draw_idle()
        
        # GPU sparkline
        self.gpu_ax.clear()
        self.gpu_ax.axis('off')
        if len(self.gpu_history) > 1:
            self.gpu_ax.plot(list(self.gpu_history), color='tab:green', linewidth=1)
            self.gpu_ax.set_ylim(0, 100)
        self.gpu_figure.tight_layout(pad=0)
        self.gpu_canvas.draw_idle()
    
    @staticmethod
    def _format_uptime(seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m"
        else:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            return f"{h}h {m}m"


class ServerManagerApp:
    """Main application window with tile-based UI."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Server Manager v2.0")
        self.root.geometry("1400x800")
        
        self.manager = ServerManager()
        self.log_viewers = {}
        self.metrics_viewers = {}
        self.tiles = {}  # server_name -> ServerTile
        self.selected_server = None
        
        # Summary stats
        self.total_cpu = 0.0
        self.total_gpu = 0.0
        self.running_count = 0
        
        self._create_widgets()
        self._create_menu()
        
        # Load configurations
        self.manager.load_configs()
        self._populate_tiles()
        
        # Start periodic UI update
        self.root.after(300, self._update_ui)
    
    def _create_widgets(self):
        """Create main UI widgets."""
        # Summary header
        summary_frame = ttk.Frame(self.root, relief=tk.RIDGE, borderwidth=2)
        summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(summary_frame, text="Dashboard Overview", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10, pady=5)
        
        self.summary_servers_label = ttk.Label(summary_frame, text="Servers: 0", font=("Arial", 10))
        self.summary_servers_label.pack(side=tk.LEFT, padx=15)
        
        self.summary_running_label = ttk.Label(summary_frame, text="Running: 0", font=("Arial", 10), foreground="green")
        self.summary_running_label.pack(side=tk.LEFT, padx=15)
        
        self.summary_cpu_label = ttk.Label(summary_frame, text="Avg CPU: -", font=("Arial", 10))
        self.summary_cpu_label.pack(side=tk.LEFT, padx=15)
        
        self.summary_gpu_label = ttk.Label(summary_frame, text="Avg GPU: -", font=("Arial", 10))
        self.summary_gpu_label.pack(side=tk.LEFT, padx=15)
        
        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Add Server", command=self._add_server).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Edit", command=self._edit_server).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete", command=self._delete_server).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Button(toolbar, text="Test Connection", command=self._test_connection).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Button(toolbar, text="Start", command=self._start_server).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Stop", command=self._stop_server).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Restart", command=self._restart_server).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Force Restart", command=self._force_restart_server).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Button(toolbar, text="View Logs", command=self._view_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="View Metrics", command=self._view_metrics).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Open Logs Folder", command=self._open_logs_folder).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Button(toolbar, text="Start All", command=self._start_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Stop All", command=self._stop_all).pack(side=tk.LEFT, padx=2)
        
        # Scrollable tile container
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        canvas = tk.Canvas(container, bg="white")
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        self.tiles_frame = ttk.Frame(canvas)
        
        self.tiles_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.tiles_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas = canvas
        
        # Context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Start", command=self._start_server)
        self.context_menu.add_command(label="Stop", command=self._stop_server)
        self.context_menu.add_command(label="Restart", command=self._restart_server)
        self.context_menu.add_command(label="Force Restart", command=self._force_restart_server)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="View Logs", command=self._view_logs)
        self.context_menu.add_command(label="View Metrics", command=self._view_metrics)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Edit", command=self._edit_server)
        self.context_menu.add_command(label="Delete", command=self._delete_server)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, padx=5, pady=2)
    
    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Add Server", command=self._add_server)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        actions_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Actions", menu=actions_menu)
        actions_menu.add_command(label="Start All", command=self._start_all)
        actions_menu.add_command(label="Stop All", command=self._stop_all)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _populate_tiles(self):
        """Create tiles in 3-column grid layout."""
        # Clear existing
        for tile in self.tiles.values():
            tile.destroy()
        self.tiles.clear()
        
        # Create tiles (3 per row)
        row, col = 0, 0
        for config in self.manager.configs:
            tile = ServerTile(self.tiles_frame, config.name, self._on_tile_click)
            tile.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
            self.tiles[config.name] = tile
            
            # Update with current state
            state = self.manager.get_worker_state(config.name)
            if state:
                tile.update_state(config, state)
            
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        # Make columns expand equally
        for i in range(3):
            self.tiles_frame.grid_columnconfigure(i, weight=1, uniform='col')
    
    def _on_tile_click(self, server_name, context_menu=False, event=None):
        """Handle tile click - select tile and optionally show context menu."""
        # Deselect previous
        if self.selected_server and self.selected_server in self.tiles:
            self.tiles[self.selected_server].mark_selected(False)
        
        # Select new
        self.selected_server = server_name
        if server_name in self.tiles:
            self.tiles[server_name].mark_selected(True)
        
        # Show context menu if right-click
        if context_menu and event:
            self.context_menu.post(event.x_root, event.y_root)
    
    def _update_ui(self):
        """Process updates from worker queue."""
        while not self.manager.ui_queue.empty():
            try:
                msg = self.manager.ui_queue.get_nowait()
                
                if msg['type'] == 'state_update':
                    server_name = msg['server']
                    state = msg['state']
                    if server_name in self.tiles:
                        config = next((c for c in self.manager.configs if c.name == server_name), None)
                        if config:
                            self.tiles[server_name].update_state(config, state)
                
                elif msg['type'] == 'metrics_update':
                    server_name = msg['server']
                    metrics = msg['metrics']
                    if server_name in self.tiles:
                        self.tiles[server_name].update_metrics(metrics)
                    # Update summary stats
                    self._update_summary()
                
                elif msg['type'] == 'log_line':
                    server_name = msg['server']
                    line = msg['line']
                    if server_name in self.log_viewers:
                        viewer = self.log_viewers[server_name]
                        if viewer.dialog.winfo_exists():
                            viewer.append_line(f"{msg['timestamp']} {line}")
            except:
                pass
        
        self.root.after(300, self._update_ui)
    
    def _update_summary(self):
        """Update summary header with aggregate stats."""
        total_servers = len(self.manager.configs)
        running = sum(1 for name in self.tiles if self.manager.get_worker_state(name) and 
                      self.manager.get_worker_state(name).status == ServerStatus.RUNNING)
        
        # Compute average CPU and GPU from all tiles
        cpu_values = []
        gpu_values = []
        for tile in self.tiles.values():
            if tile.metrics.get('cpu') is not None:
                cpu_values.append(tile.metrics['cpu'])
            if tile.metrics.get('gpu_util') is not None:
                gpu_values.append(tile.metrics['gpu_util'])
        
        avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else None
        avg_gpu = sum(gpu_values) / len(gpu_values) if gpu_values else None
        
        self.summary_servers_label.config(text=f"Servers: {total_servers}")
        self.summary_running_label.config(text=f"⚡ Running: {running}")
        self.summary_cpu_label.config(text=f"Avg CPU: {avg_cpu:.1f}%" if avg_cpu is not None else "Avg CPU: -")
        self.summary_gpu_label.config(text=f"Avg GPU: {avg_gpu:.1f}%" if avg_gpu is not None else "Avg GPU: -")
    
    # === Action Methods (same as before) ===
    
    def _add_server(self):
        dialog = ServerFormDialog(self.root)
        config = dialog.show()
        if config:
            try:
                self.manager.add_server(config)
                self._populate_tiles()
                self.status_var.set(f"Added server: {config.name}")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)
    
    def _edit_server(self):
        if not self.selected_server:
            messagebox.showwarning("No Selection", "Please select a server to edit", parent=self.root)
            return
        config = next((c for c in self.manager.configs if c.name == self.selected_server), None)
        if not config:
            return
        dialog = ServerFormDialog(self.root, config=config)
        new_config = dialog.show()
        if new_config:
            try:
                self.manager.edit_server(self.selected_server, new_config)
                self._populate_tiles()
                self.status_var.set(f"Edited server: {new_config.name}")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)
    
    def _delete_server(self):
        if not self.selected_server:
            messagebox.showwarning("No Selection", "Please select a server to delete", parent=self.root)
            return
        if messagebox.askyesno("Confirm Delete", f"Delete server '{self.selected_server}'?", parent=self.root):
            try:
                self.manager.delete_server(self.selected_server)
                self._populate_tiles()
                self.selected_server = None
                self.status_var.set("Server deleted")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)
    
    def _test_connection(self):
        if not self.selected_server:
            messagebox.showwarning("No Selection", "Please select a server to test", parent=self.root)
            return
        config = next((c for c in self.manager.configs if c.name == self.selected_server), None)
        if not config:
            return
        self.status_var.set(f"Testing connection to {self.selected_server}...")
        self.root.update()
        
        def test_thread():
            success, info = self.manager.test_connection(config)
            def show_result():
                if success:
                    msg = f"Connection successful!\n\nOS: {info.get('os', 'Unknown')}\nPython: {info.get('python', 'Not found')}\n"
                    if 'python_version' in info:
                        msg += f"Version: {info['python_version']}\n"
                    messagebox.showinfo("Test Connection", msg, parent=self.root)
                else:
                    messagebox.showerror("Test Connection Failed", info.get('error', 'Unknown error'), parent=self.root)
                self.status_var.set("Ready")
            self.root.after(0, show_result)
        threading.Thread(target=test_thread, daemon=True).start()
    
    def _start_server(self):
        if not self.selected_server:
            return
        self.manager.start_server(self.selected_server)
        self.status_var.set(f"Starting {self.selected_server}...")
    
    def _stop_server(self):
        if not self.selected_server:
            return
        if messagebox.askyesno("Confirm Stop", f"Stop server '{self.selected_server}'?", parent=self.root):
            self.manager.stop_server(self.selected_server)
            self.status_var.set(f"Stopping {self.selected_server}...")
    
    def _restart_server(self):
        if not self.selected_server:
            return
        self.manager.restart_server(self.selected_server)
        self.status_var.set(f"Restarting {self.selected_server}...")
    
    def _force_restart_server(self):
        if not self.selected_server:
            return
        if messagebox.askyesno("Confirm Force Restart", f"Force restart '{self.selected_server}'?", parent=self.root):
            self.manager.force_restart_server(self.selected_server)
            self.status_var.set(f"Force restarting {self.selected_server}...")
    
    def _view_logs(self):
        if not self.selected_server:
            messagebox.showwarning("No Selection", "Please select a server to view logs", parent=self.root)
            return
        if self.selected_server in self.log_viewers:
            viewer = self.log_viewers[self.selected_server]
            if viewer.dialog.winfo_exists():
                viewer.dialog.lift()
                return
        viewer = LogViewerDialog(self.root, self.selected_server)
        self.log_viewers[self.selected_server] = viewer
    
    def _view_metrics(self):
        if not self.selected_server:
            messagebox.showwarning("No Selection", "Please select a server to view metrics", parent=self.root)
            return
        if self.selected_server in self.metrics_viewers:
            viewer = self.metrics_viewers[self.selected_server]
            if viewer.dialog.winfo_exists():
                viewer.dialog.lift()
                return
        viewer = MetricsViewerDialog(self.root, self.selected_server)
        self.metrics_viewers[self.selected_server] = viewer
    
    def _open_logs_folder(self):
        logs_dir = os.path.abspath("logs")
        if os.path.exists(logs_dir):
            os.startfile(logs_dir)
    
    def _start_all(self):
        self.manager.start_all()
        self.status_var.set("Starting all servers...")
    
    def _stop_all(self):
        if messagebox.askyesno("Confirm Stop All", "Stop all servers?", parent=self.root):
            self.manager.stop_all()
            self.status_var.set("Stopping all servers...")
    
    def _show_about(self):
        messagebox.showinfo(
            "About",
            "Server Manager v2.0\n\n"
            "Manages and monitors remote server processes via SSH.\n"
            "Automatically restarts processes on failure or server reboot.\n"
            "Real-time CPU, GPU, and RAM metrics with historical graphing.",
            parent=self.root
        )
    
    def run(self):
        """Run the application."""
        self.root.mainloop()


if __name__ == "__main__":
    app = ServerManagerApp()
    app.run()
