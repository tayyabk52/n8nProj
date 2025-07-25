import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

class ScraperSettingsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Google Maps Scraper Settings")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Default settings
        self.settings = {
            "headless_mode": True,
            "window_width": 1920,
            "window_height": 1080,
            "page_load_wait": 8,
            "results_wait": 20,
            "scroll_attempts": 15,
            "scroll_delay": 2,
            "extraction_delay": 0.3,
            "max_retries": 3,
            "default_zoom_level": 14,
            "user_agent_rotation": True,
            "enable_gpu": False,
            "debug_mode": False
        }
        
        self.load_settings()
        self.create_widgets()
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Google Maps Scraper Configuration", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Browser Settings
        browser_frame = ttk.LabelFrame(main_frame, text="Browser Settings", padding="10")
        browser_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Headless mode
        self.headless_var = tk.BooleanVar(value=self.settings["headless_mode"])
        ttk.Checkbutton(browser_frame, text="Headless Mode (No GUI)", 
                       variable=self.headless_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Window size
        ttk.Label(browser_frame, text="Window Width:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.width_var = tk.StringVar(value=str(self.settings["window_width"]))
        ttk.Entry(browser_frame, textvariable=self.width_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(browser_frame, text="Window Height:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.height_var = tk.StringVar(value=str(self.settings["window_height"]))
        ttk.Entry(browser_frame, textvariable=self.height_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        # GPU and User Agent
        self.gpu_var = tk.BooleanVar(value=self.settings["enable_gpu"])
        ttk.Checkbutton(browser_frame, text="Enable GPU", 
                       variable=self.gpu_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        self.ua_rotation_var = tk.BooleanVar(value=self.settings["user_agent_rotation"])
        ttk.Checkbutton(browser_frame, text="User Agent Rotation", 
                       variable=self.ua_rotation_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Timing Settings
        timing_frame = ttk.LabelFrame(main_frame, text="Timing Settings", padding="10")
        timing_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Page load wait
        ttk.Label(timing_frame, text="Page Load Wait (seconds):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.page_wait_var = tk.StringVar(value=str(self.settings["page_load_wait"]))
        ttk.Entry(timing_frame, textvariable=self.page_wait_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Results wait
        ttk.Label(timing_frame, text="Results Wait Timeout (seconds):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.results_wait_var = tk.StringVar(value=str(self.settings["results_wait"]))
        ttk.Entry(timing_frame, textvariable=self.results_wait_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        # Scroll settings
        ttk.Label(timing_frame, text="Scroll Attempts:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.scroll_attempts_var = tk.StringVar(value=str(self.settings["scroll_attempts"]))
        ttk.Entry(timing_frame, textvariable=self.scroll_attempts_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(timing_frame, text="Scroll Delay (seconds):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.scroll_delay_var = tk.StringVar(value=str(self.settings["scroll_delay"]))
        ttk.Entry(timing_frame, textvariable=self.scroll_delay_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=(10, 0))
        
        # Extraction delay
        ttk.Label(timing_frame, text="Extraction Delay (seconds):").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.extraction_delay_var = tk.StringVar(value=str(self.settings["extraction_delay"]))
        ttk.Entry(timing_frame, textvariable=self.extraction_delay_var, width=10).grid(row=4, column=1, sticky=tk.W, padx=(10, 0))
        
        # Advanced Settings
        advanced_frame = ttk.LabelFrame(main_frame, text="Advanced Settings", padding="10")
        advanced_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Max retries
        ttk.Label(advanced_frame, text="Max Retries:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.retries_var = tk.StringVar(value=str(self.settings["max_retries"]))
        ttk.Entry(advanced_frame, textvariable=self.retries_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Default zoom
        ttk.Label(advanced_frame, text="Default Zoom Level:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.zoom_var = tk.StringVar(value=str(self.settings["default_zoom_level"]))
        ttk.Entry(advanced_frame, textvariable=self.zoom_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        # Debug mode
        self.debug_var = tk.BooleanVar(value=self.settings["debug_mode"])
        ttk.Checkbutton(advanced_frame, text="Debug Mode (Verbose Logging)", 
                       variable=self.debug_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(button_frame, text="Save Settings", 
                  command=self.save_settings).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="Load Settings", 
                  command=self.load_settings).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text="Reset to Defaults", 
                  command=self.reset_defaults).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(button_frame, text="Apply & Close", 
                  command=self.apply_and_close).grid(row=0, column=3)
        
        # Status
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, 
                                foreground="green")
        status_label.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists("scraper_settings.json"):
                with open("scraper_settings.json", "r") as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
                    self.update_gui()
                    self.status_var.set("Settings loaded successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {e}")
    
    def save_settings(self):
        """Save settings to file"""
        try:
            self.collect_settings()
            with open("scraper_settings.json", "w") as f:
                json.dump(self.settings, f, indent=2)
            self.status_var.set("Settings saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def collect_settings(self):
        """Collect settings from GUI"""
        try:
            self.settings.update({
                "headless_mode": self.headless_var.get(),
                "window_width": int(self.width_var.get()),
                "window_height": int(self.height_var.get()),
                "page_load_wait": float(self.page_wait_var.get()),
                "results_wait": int(self.results_wait_var.get()),
                "scroll_attempts": int(self.scroll_attempts_var.get()),
                "scroll_delay": float(self.scroll_delay_var.get()),
                "extraction_delay": float(self.extraction_delay_var.get()),
                "max_retries": int(self.retries_var.get()),
                "default_zoom_level": int(self.zoom_var.get()),
                "user_agent_rotation": self.ua_rotation_var.get(),
                "enable_gpu": self.gpu_var.get(),
                "debug_mode": self.debug_var.get()
            })
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
            raise
    
    def update_gui(self):
        """Update GUI with current settings"""
        self.headless_var.set(self.settings["headless_mode"])
        self.width_var.set(str(self.settings["window_width"]))
        self.height_var.set(str(self.settings["window_height"]))
        self.page_wait_var.set(str(self.settings["page_load_wait"]))
        self.results_wait_var.set(str(self.settings["results_wait"]))
        self.scroll_attempts_var.set(str(self.settings["scroll_attempts"]))
        self.scroll_delay_var.set(str(self.settings["scroll_delay"]))
        self.extraction_delay_var.set(str(self.settings["extraction_delay"]))
        self.retries_var.set(str(self.settings["max_retries"]))
        self.zoom_var.set(str(self.settings["default_zoom_level"]))
        self.ua_rotation_var.set(self.settings["user_agent_rotation"])
        self.gpu_var.set(self.settings["enable_gpu"])
        self.debug_var.set(self.settings["debug_mode"])
    
    def reset_defaults(self):
        """Reset to default settings"""
        self.settings = {
            "headless_mode": True,
            "window_width": 1920,
            "window_height": 1080,
            "page_load_wait": 8,
            "results_wait": 20,
            "scroll_attempts": 15,
            "scroll_delay": 2,
            "extraction_delay": 0.3,
            "max_retries": 3,
            "default_zoom_level": 14,
            "user_agent_rotation": True,
            "enable_gpu": False,
            "debug_mode": False
        }
        self.update_gui()
        self.status_var.set("Reset to defaults")
    
    def apply_and_close(self):
        """Apply settings and close"""
        try:
            self.collect_settings()
            self.save_settings()
            self.root.destroy()
        except:
            pass  # Error already shown by collect_settings

def main():
    root = tk.Tk()
    app = ScraperSettingsGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 