"""Add/Edit Server Dialog."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional
from models import ServerConfig


class ServerFormDialog:
    """Dialog for adding or editing a server configuration."""
    
    def __init__(self, parent, config: Optional[ServerConfig] = None):
        self.parent = parent
        self.config = config  # If editing, this is the existing config
        self.result: Optional[ServerConfig] = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Server" if config is None else "Edit Server")
        self.dialog.geometry("650x800")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._populate_fields()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """Create form widgets."""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Name
        ttk.Label(main_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        # Host
        ttk.Label(main_frame, text="Host:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.host_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.host_var, width=40).grid(row=1, column=1, sticky=tk.EW, pady=5)
        
        # Port
        ttk.Label(main_frame, text="Port:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.port_var = tk.StringVar(value="22")
        ttk.Entry(main_frame, textvariable=self.port_var, width=40).grid(row=2, column=1, sticky=tk.EW, pady=5)
        
        # Username
        ttk.Label(main_frame, text="Username:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.username_var = tk.StringVar(value="root")
        ttk.Entry(main_frame, textvariable=self.username_var, width=40).grid(row=3, column=1, sticky=tk.EW, pady=5)
        
        # Auth Type
        ttk.Label(main_frame, text="Auth Type:").grid(row=4, column=0, sticky=tk.W, pady=5)
        auth_frame = ttk.Frame(main_frame)
        auth_frame.grid(row=4, column=1, sticky=tk.EW, pady=5)
        
        self.auth_type_var = tk.StringVar(value="key")
        ttk.Radiobutton(auth_frame, text="Private Key", variable=self.auth_type_var, value="key", command=self._toggle_auth_fields).pack(side=tk.LEFT)
        ttk.Radiobutton(auth_frame, text="Password", variable=self.auth_type_var, value="password", command=self._toggle_auth_fields).pack(side=tk.LEFT, padx=10)
        
        # Key Path
        ttk.Label(main_frame, text="Key Path:").grid(row=5, column=0, sticky=tk.W, pady=5)
        key_frame = ttk.Frame(main_frame)
        key_frame.grid(row=5, column=1, sticky=tk.EW, pady=5)
        
        self.key_path_var = tk.StringVar()
        self.key_path_entry = ttk.Entry(key_frame, textvariable=self.key_path_var)
        self.key_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(key_frame, text="Browse", command=self._browse_key).pack(side=tk.LEFT, padx=(5, 0))
        
        # Passphrase
        ttk.Label(main_frame, text="Passphrase (optional):").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.passphrase_var = tk.StringVar()
        self.passphrase_entry = ttk.Entry(main_frame, textvariable=self.passphrase_var, show="*", width=40)
        self.passphrase_entry.grid(row=6, column=1, sticky=tk.EW, pady=5)
        
        # Password
        ttk.Label(main_frame, text="Password:").grid(row=7, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(main_frame, textvariable=self.password_var, show="*", width=40)
        self.password_entry.grid(row=7, column=1, sticky=tk.EW, pady=5)
        
        # Command
        ttk.Label(main_frame, text="Command:").grid(row=8, column=0, sticky=tk.W, pady=5)
        self.command_var = tk.StringVar(value="python3 /home/v13/ultra_aggressive_worker.py")
        ttk.Entry(main_frame, textvariable=self.command_var, width=40).grid(row=8, column=1, sticky=tk.EW, pady=5)
        
        # Working Directory
        ttk.Label(main_frame, text="Working Dir:").grid(row=9, column=0, sticky=tk.W, pady=5)
        self.working_dir_var = tk.StringVar(value="/home/v13")
        ttk.Entry(main_frame, textvariable=self.working_dir_var, width=40).grid(row=9, column=1, sticky=tk.EW, pady=5)
        
        # Restart Delay
        ttk.Label(main_frame, text="Restart Delay (seconds):").grid(row=10, column=0, sticky=tk.W, pady=5)
        self.restart_delay_var = tk.StringVar(value="12")
        ttk.Entry(main_frame, textvariable=self.restart_delay_var, width=40).grid(row=10, column=1, sticky=tk.EW, pady=5)
        
        # Stop Command
        ttk.Label(main_frame, text="Stop Command:").grid(row=11, column=0, sticky=tk.W, pady=5)
        self.stop_command_var = tk.StringVar(value="pkill -f ultra_aggressive_worker.py")
        ttk.Entry(main_frame, textvariable=self.stop_command_var, width=40).grid(row=11, column=1, sticky=tk.EW, pady=5)
        
        # Pre-Command (optional)
        ttk.Label(main_frame, text="Pre-Command (optional):").grid(row=12, column=0, sticky=tk.W, pady=5)
        self.pre_command_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.pre_command_var, width=40).grid(row=12, column=1, sticky=tk.EW, pady=5)
        
        # Enabled
        self.enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="Enabled", variable=self.enabled_var).grid(row=13, column=1, sticky=tk.W, pady=5)
        
        # Health Check Section
        ttk.Separator(main_frame, orient='horizontal').grid(row=14, column=0, columnspan=2, sticky=tk.EW, pady=10)
        ttk.Label(main_frame, text="Health Checks:", font=('TkDefaultFont', 9, 'bold')).grid(row=15, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Health Check Enabled
        self.health_check_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="Enable Health Checks", variable=self.health_check_enabled_var, command=self._toggle_health_fields).grid(row=16, column=1, sticky=tk.W, pady=5)
        
        # CPU Health Check
        self.health_check_cpu_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="Monitor CPU Usage", variable=self.health_check_cpu_enabled_var).grid(row=17, column=1, sticky=tk.W, pady=5)
        
        cpu_frame = ttk.Frame(main_frame)
        cpu_frame.grid(row=18, column=1, sticky=tk.W, pady=2)
        ttk.Label(cpu_frame, text="Restart if CPU <").pack(side=tk.LEFT)
        self.health_check_cpu_threshold_var = tk.StringVar(value="50")
        self.cpu_threshold_entry = ttk.Entry(cpu_frame, textvariable=self.health_check_cpu_threshold_var, width=8)
        self.cpu_threshold_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(cpu_frame, text="% for").pack(side=tk.LEFT)
        self.health_check_cpu_duration_var = tk.StringVar(value="100")
        self.cpu_duration_entry = ttk.Entry(cpu_frame, textvariable=self.health_check_cpu_duration_var, width=8)
        self.cpu_duration_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(cpu_frame, text="seconds").pack(side=tk.LEFT)
        
        # GPU Health Check
        self.health_check_gpu_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="Monitor GPU Usage", variable=self.health_check_gpu_enabled_var).grid(row=19, column=1, sticky=tk.W, pady=5)
        
        gpu_frame = ttk.Frame(main_frame)
        gpu_frame.grid(row=20, column=1, sticky=tk.W, pady=2)
        ttk.Label(gpu_frame, text="Restart if GPU <").pack(side=tk.LEFT)
        self.health_check_gpu_threshold_var = tk.StringVar(value="50")
        self.gpu_threshold_entry = ttk.Entry(gpu_frame, textvariable=self.health_check_gpu_threshold_var, width=8)
        self.gpu_threshold_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(gpu_frame, text="% for").pack(side=tk.LEFT)
        self.health_check_gpu_duration_var = tk.StringVar(value="100")
        self.gpu_duration_entry = ttk.Entry(gpu_frame, textvariable=self.health_check_gpu_duration_var, width=8)
        self.gpu_duration_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(gpu_frame, text="seconds").pack(side=tk.LEFT)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=21, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Save", command=self._save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Make column 1 expandable
        main_frame.columnconfigure(1, weight=1)
        
        self._toggle_auth_fields()
        self._toggle_health_fields()
    
    def _toggle_auth_fields(self):
        """Enable/disable auth fields based on selected type."""
        auth_type = self.auth_type_var.get()
        
        if auth_type == "key":
            self.key_path_entry.config(state=tk.NORMAL)
            self.passphrase_entry.config(state=tk.NORMAL)
            self.password_entry.config(state=tk.DISABLED)
        else:
            self.key_path_entry.config(state=tk.DISABLED)
            self.passphrase_entry.config(state=tk.DISABLED)
            self.password_entry.config(state=tk.NORMAL)
    
    def _toggle_health_fields(self):
        """Enable/disable health check fields based on enabled status."""
        enabled = self.health_check_enabled_var.get()
        state = tk.NORMAL if enabled else tk.DISABLED
        
        # Toggle all health check widgets
        for widget in [self.cpu_threshold_entry, self.cpu_duration_entry,
                       self.gpu_threshold_entry, self.gpu_duration_entry]:
            widget.config(state=state)
    
    def _browse_key(self):
        """Open file dialog to select private key."""
        filename = filedialog.askopenfilename(
            title="Select Private Key",
            parent=self.dialog
        )
        if filename:
            # Normalize path for cross-platform consistency
            filename = filename.replace('\\', '/')
            self.key_path_var.set(filename)
    
    def _populate_fields(self):
        """Populate fields if editing existing config."""
        if self.config:
            self.name_var.set(self.config.name)
            self.host_var.set(self.config.host)
            self.port_var.set(str(self.config.port))
            self.username_var.set(self.config.username)
            self.command_var.set(self.config.command)
            self.working_dir_var.set(self.config.working_dir)
            self.restart_delay_var.set(str(self.config.restart_delay_seconds))
            self.stop_command_var.set(self.config.stop_command)
            self.pre_command_var.set(getattr(self.config, 'pre_command', '') or '')
            self.enabled_var.set(self.config.enabled)
            
            # Auth
            auth_type = self.config.auth.get('type', 'key')
            self.auth_type_var.set(auth_type)
            
            if auth_type == 'key':
                self.key_path_var.set(self.config.auth.get('key_path', ''))
                self.passphrase_var.set(self.config.auth.get('passphrase', '') or '')
            else:
                self.password_var.set(self.config.auth.get('password', ''))
            
            # Health checks
            self.health_check_enabled_var.set(getattr(self.config, 'health_check_enabled', False))
            self.health_check_cpu_enabled_var.set(getattr(self.config, 'health_check_cpu_enabled', False))
            self.health_check_cpu_threshold_var.set(str(getattr(self.config, 'health_check_cpu_threshold', 50.0)))
            self.health_check_cpu_duration_var.set(str(getattr(self.config, 'health_check_cpu_duration', 100)))
            self.health_check_gpu_enabled_var.set(getattr(self.config, 'health_check_gpu_enabled', False))
            self.health_check_gpu_threshold_var.set(str(getattr(self.config, 'health_check_gpu_threshold', 50.0)))
            self.health_check_gpu_duration_var.set(str(getattr(self.config, 'health_check_gpu_duration', 100)))
            
            self._toggle_auth_fields()
    
    def _validate(self) -> bool:
        """Validate form inputs."""
        if not self.name_var.get().strip():
            messagebox.showerror("Validation Error", "Name is required", parent=self.dialog)
            return False
        
        if not self.host_var.get().strip():
            messagebox.showerror("Validation Error", "Host is required", parent=self.dialog)
            return False
        
        try:
            port = int(self.port_var.get())
            if port < 1 or port > 65535:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "Port must be a number between 1 and 65535", parent=self.dialog)
            return False
        
        if not self.username_var.get().strip():
            messagebox.showerror("Validation Error", "Username is required", parent=self.dialog)
            return False
        
        auth_type = self.auth_type_var.get()
        if auth_type == 'key' and not self.key_path_var.get().strip():
            messagebox.showerror("Validation Error", "Key path is required for key authentication", parent=self.dialog)
            return False
        
        if auth_type == 'password' and not self.password_var.get().strip():
            messagebox.showerror("Validation Error", "Password is required for password authentication", parent=self.dialog)
            return False
        
        try:
            restart_delay = int(self.restart_delay_var.get())
            if restart_delay < 1:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "Restart delay must be a positive number", parent=self.dialog)
            return False
        
        # Health check validation
        if self.health_check_enabled_var.get():
            if self.health_check_cpu_enabled_var.get():
                try:
                    cpu_threshold = float(self.health_check_cpu_threshold_var.get())
                    if cpu_threshold < 0 or cpu_threshold > 100:
                        raise ValueError()
                except ValueError:
                    messagebox.showerror("Validation Error", "CPU threshold must be between 0 and 100", parent=self.dialog)
                    return False
                
                try:
                    cpu_duration = int(self.health_check_cpu_duration_var.get())
                    if cpu_duration < 1:
                        raise ValueError()
                except ValueError:
                    messagebox.showerror("Validation Error", "CPU duration must be a positive number", parent=self.dialog)
                    return False
            
            if self.health_check_gpu_enabled_var.get():
                try:
                    gpu_threshold = float(self.health_check_gpu_threshold_var.get())
                    if gpu_threshold < 0 or gpu_threshold > 100:
                        raise ValueError()
                except ValueError:
                    messagebox.showerror("Validation Error", "GPU threshold must be between 0 and 100", parent=self.dialog)
                    return False
                
                try:
                    gpu_duration = int(self.health_check_gpu_duration_var.get())
                    if gpu_duration < 1:
                        raise ValueError()
                except ValueError:
                    messagebox.showerror("Validation Error", "GPU duration must be a positive number", parent=self.dialog)
                    return False
        
        return True
    
    def _save(self):
        """Save configuration and close dialog."""
        if not self._validate():
            return
        
        # Build auth dict
        auth_type = self.auth_type_var.get()
        if auth_type == 'key':
            auth = {
                'type': 'key',
                'key_path': self.key_path_var.get().strip(),
                'passphrase': self.passphrase_var.get().strip() or None
            }
        else:
            auth = {
                'type': 'password',
                'password': self.password_var.get().strip()
            }
        
        # Create config
        self.result = ServerConfig(
            name=self.name_var.get().strip(),
            host=self.host_var.get().strip(),
            port=int(self.port_var.get()),
            username=self.username_var.get().strip(),
            auth=auth,
            command=self.command_var.get().strip(),
            working_dir=self.working_dir_var.get().strip(),
            restart_delay_seconds=int(self.restart_delay_var.get()),
            stop_command=self.stop_command_var.get().strip(),
            pre_command=self.pre_command_var.get().strip(),
            enabled=self.enabled_var.get(),
            health_check_enabled=self.health_check_enabled_var.get(),
            health_check_cpu_enabled=self.health_check_cpu_enabled_var.get(),
            health_check_cpu_threshold=float(self.health_check_cpu_threshold_var.get()),
            health_check_cpu_duration=int(self.health_check_cpu_duration_var.get()),
            health_check_gpu_enabled=self.health_check_gpu_enabled_var.get(),
            health_check_gpu_threshold=float(self.health_check_gpu_threshold_var.get()),
            health_check_gpu_duration=int(self.health_check_gpu_duration_var.get())
        )
        
        self.dialog.destroy()
    
    def show(self) -> Optional[ServerConfig]:
        """Show dialog and return result."""
        self.dialog.wait_window()
        return self.result
