#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
from pathlib import Path

class OllamaCodeCheckerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ollama Code Checker")
        self.root.geometry("900x700")
        
        # Configuration
        self.models_path = "/run/media/garuda/73cf9511-0af0-4ac4-9d83-ee21eb17ff5d/models"
        
        # Variables
        self.analysis_running = False
        self.current_process = None
        self.analyzed_files = []  # Store files from last analysis
        self.last_analysis_target = None
        self.last_analysis_type = None
        
        self.setup_ui()
        self.load_available_models()
        self.start_ollama_service()
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🤖 Ollama Code Analysis Tool", 
                               font=('Arial', 18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Model selection
        ttk.Label(main_frame, text="AI Model:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.model_var = tk.StringVar(value="granite-code:latest")
        self.model_combo = ttk.Combobox(main_frame, textvariable=self.model_var, width=50, font=('Arial', 9))
        self.model_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Analysis type
        ttk.Label(main_frame, text="Analysis Type:", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.analysis_var = tk.StringVar(value="cleanup")
        analysis_frame = ttk.Frame(main_frame)
        analysis_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        analysis_options = [
            ("🐛 Errors & Bugs", "errors"),
            ("🎨 Code Style", "style"),
            ("🔒 Security", "security"),
            ("⚡ Performance", "performance"),
            ("🧹 Cleanup (Stub/Unused)", "cleanup"),
            ("📋 All", "all")
        ]
        
        for i, (text, value) in enumerate(analysis_options):
            ttk.Radiobutton(analysis_frame, text=text, variable=self.analysis_var, 
                           value=value).grid(row=i//3, column=i%3, padx=(0, 15), pady=2, sticky=tk.W)
        
        # Target selection
        ttk.Label(main_frame, text="Target:", font=('Arial', 10, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=5)
        target_frame = ttk.Frame(main_frame)
        target_frame.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        target_frame.columnconfigure(0, weight=1)
        
        self.target_var = tk.StringVar(value="/home/garuda/disability-app-tauri")
        self.target_entry = ttk.Entry(target_frame, textvariable=self.target_var, font=('Arial', 9))
        self.target_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Bind target change to auto-suggest model
        self.target_var.trace('w', self.on_target_change)
        
        ttk.Button(target_frame, text="📁 Browse Dir", 
                  command=self.browse_directory).grid(row=0, column=1)
        ttk.Button(target_frame, text="📄 Browse File", 
                  command=self.browse_file).grid(row=0, column=2, padx=(5, 0))
        ttk.Button(target_frame, text="🤖 Auto-Select Model", 
                  command=self.auto_select_model).grid(row=0, column=3, padx=(5, 0))
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        self.analyze_button = ttk.Button(button_frame, text="🚀 Start Analysis", 
                                        command=self.start_analysis, 
                                        style='Accent.TButton')
        self.analyze_button.grid(row=0, column=0, padx=(0, 10))
        
        self.fix_button = ttk.Button(button_frame, text="🔧 Fix Issues", 
                                    command=self.start_fix_only, 
                                    state=tk.DISABLED,
                                    style='Accent.TButton')
        self.fix_button.grid(row=0, column=1, padx=(0, 10))
        
        self.autofix_button = ttk.Button(button_frame, text="⚡ Analyze & Auto-Fix", 
                                        command=self.start_autofix_analysis, 
                                        style='Accent.TButton')
        self.autofix_button.grid(row=0, column=2, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ Stop Analysis", 
                                     command=self.stop_analysis, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=3, padx=(0, 10))
        
        ttk.Button(button_frame, text="📂 Load Results", 
                  command=self.load_previous_results).grid(row=0, column=4, padx=(0, 10))
        
        ttk.Button(button_frame, text="🗑️ Clear Output", 
                  command=self.clear_output).grid(row=0, column=5, padx=(0, 10))
        
        ttk.Button(button_frame, text="💾 Save Report", 
                  command=self.save_report).grid(row=0, column=6)
        
        # Output area
        output_frame = ttk.LabelFrame(main_frame, text="📊 Analysis Output", padding="5")
        output_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, 
                                                    height=25, state=tk.DISABLED,
                                                    font=('Consolas', 9))
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready - Select model and target, then click Start Analysis")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, 
                              font=('Arial', 9))
        status_bar.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def start_ollama_service(self):
        """Start Ollama service in background"""
        def start_service():
            try:
                # Kill any existing ollama processes
                subprocess.run(['pkill', '-f', 'ollama serve'], capture_output=True)
                
                # Start ollama with custom models path
                env = os.environ.copy()
                env['OLLAMA_MODELS'] = self.models_path
                
                subprocess.Popen(['ollama', 'serve'], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL, 
                               env=env)
                
                self.root.after(0, lambda: self.status_var.set("Ollama service started - Ready for analysis"))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Warning: Could not start Ollama service: {e}"))
        
        threading.Thread(target=start_service, daemon=True).start()
    
    def load_available_models(self):
        """Load available Ollama models"""
        try:
            # Try to get models from manifest directory first
            manifest_path = f"{self.models_path}/manifests/registry.ollama.ai/library"
            if os.path.exists(manifest_path):
                model_dirs = [d for d in os.listdir(manifest_path) 
                             if os.path.isdir(os.path.join(manifest_path, d))]
                
                if model_dirs:
                    # Separate code models from others
                    code_models = []
                    other_models = []
                    
                    for model in sorted(model_dirs):
                        model_name = f"{model}:latest"
                        if any(x in model.lower() for x in ['code', 'granite', 'deepseek']):
                            code_models.append(f"🚀 {model_name}")
                        else:
                            other_models.append(model_name)
                    
                    # Combine with code models first
                    all_models = code_models + other_models
                    self.model_combo['values'] = all_models
                    
                    if code_models:
                        self.model_var.set(code_models[0])
                    return
        
        except Exception as e:
            print(f"Warning: Could not load models: {e}")
        
        # Fallback models
        fallback_models = [
            '🚀 granite-code:latest', '🚀 deepseek-coder-v2:latest', '🚀 qwen2.5-coder:latest',
            '🚀 codellama:latest', '🚀 codegemma:latest', 'llama3.1:latest'
        ]
        self.model_combo['values'] = fallback_models
        self.model_var.set('🚀 granite-code:latest')
    
    def browse_directory(self):
        """Browse for directory"""
        directory = filedialog.askdirectory(initialdir=self.target_var.get())
        if directory:
            self.target_var.set(directory)
            # Auto-suggest model when directory is selected
            self.auto_select_model()
    
    def browse_file(self):
        """Browse for file"""
        file_path = filedialog.askopenfilename(
            initialdir=os.path.dirname(self.target_var.get()),
            filetypes=[
                ("Code files", "*.py *.rs *.ts *.tsx *.js *.jsx *.go *.java *.cpp *.c *.h"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.target_var.set(file_path)
            # Auto-suggest model when file is selected
            self.auto_select_model()
    
    def append_output(self, text):
        """Append text to output area"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def clear_output(self):
        """Clear output area"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
    
    def save_report(self):
        """Save analysis report to file"""
        if not self.output_text.get(1.0, tk.END).strip():
            messagebox.showwarning("No Content", "No analysis output to save.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.output_text.get(1.0, tk.END))
                messagebox.showinfo("Saved", f"Report saved to {file_path}")
                self.status_var.set(f"Report saved: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}")
    
    def start_analysis(self):
        """Start code analysis"""
        if self.analysis_running:
            return
        
        target = self.target_var.get().strip()
        if not target:
            messagebox.showerror("Error", "Please select a target file or directory.")
            return
        
        if not os.path.exists(target):
            messagebox.showerror("Error", f"Target path does not exist: {target}")
            return
        
        # Clean model name (remove emoji prefix)
        model = self.model_var.get().replace('🚀 ', '').strip()
        
        self.analysis_running = True
        self.analyze_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress.start()
        self.status_var.set("Running analysis...")
        
        # Clear previous output
        self.clear_output()
        
        # Run analysis in separate thread
        thread = threading.Thread(target=self.run_analysis)
        thread.daemon = True
        thread.start()
    
    def stop_analysis(self):
        """Stop running analysis"""
        if self.current_process:
            self.current_process.terminate()
        self.analysis_finished()
        self.append_output("\n🛑 Analysis stopped by user\n")
    
    def start_autofix_analysis(self):
        """Start analysis with auto-fix capability"""
        if self.analysis_running:
            return
        
        target = self.target_var.get().strip()
        if not target:
            messagebox.showerror("Error", "Please select a target file or directory.")
            return
        
        if not os.path.exists(target):
            messagebox.showerror("Error", f"Target path does not exist: {target}")
            return
        
        # Confirm auto-fix action
        result = messagebox.askyesno(
            "Auto-Fix Confirmation", 
            "This will analyze and automatically fix issues in your code.\n\n"
            "⚠️ IMPORTANT: This will modify your files!\n\n"
            "Make sure you have backups or are using version control.\n\n"
            "Do you want to continue?"
        )
        
        if not result:
            return
        
        # Clean model name (remove emoji prefix)
        model = self.model_var.get().replace('🚀 ', '').strip()
        
        self.analysis_running = True
        self.analyze_button.config(state=tk.DISABLED)
        self.autofix_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress.start()
        self.status_var.set("Running analysis with auto-fix...")
        
        # Clear previous output
        self.clear_output()
        
        # Run analysis in separate thread
        thread = threading.Thread(target=self.run_autofix_analysis)
        thread.daemon = True
        thread.start()
    
    def run_analysis(self):
        """Run the actual analysis using direct ollama commands"""
        try:
            target = self.target_var.get().strip()
            model = self.model_var.get().replace('🚀 ', '').strip()
            analysis_type = self.analysis_var.get()
            
            self.append_output("🚀 Starting Ollama Code Analysis\n")
            self.append_output("=" * 50 + "\n")
            self.append_output(f"📁 Target: {target}\n")
            self.append_output(f"🤖 Model: {model}\n")
            self.append_output(f"🔍 Analysis: {analysis_type}\n")
            self.append_output("=" * 50 + "\n\n")
            
            # Set environment
            env = os.environ.copy()
            env['OLLAMA_MODELS'] = self.models_path
            env['CUDA_VISIBLE_DEVICES'] = '0'  # Use GPU
            
            if os.path.isfile(target):
                files_to_analyze = [target]
            else:
                # Find code files in directory
                extensions = ['.rs', '.ts', '.tsx', '.js', '.jsx', '.py', '.go', '.java', '.cpp', '.c', '.h']
                files_to_analyze = []
                for root, dirs, files in os.walk(target):
                    # Skip common build/dependency directories
                    dirs[:] = [d for d in dirs if d not in ['node_modules', 'target', 'build', 'dist', '.git', '__pycache__']]
                    for file in files:
                        if any(file.endswith(ext) for ext in extensions):
                            file_path = os.path.join(root, file)
                            # Skip very large files (>50KB)
                            try:
                                if os.path.getsize(file_path) < 50000:  # 50KB limit
                                    files_to_analyze.append(file_path)
                            except OSError:
                                pass  # Skip if can't get file size
            
            if not files_to_analyze:
                self.append_output("⚠️ No code files found to analyze.\n")
                return
            
            # Show warning for large codebases
            if len(files_to_analyze) > 100:
                self.append_output(f"⚠️  Large codebase detected: {len(files_to_analyze)} files\n")
                self.append_output("This may take a while. Consider analyzing smaller directories first.\n\n")
            else:
                self.append_output(f"📊 Found {len(files_to_analyze)} files to analyze\n\n")
            
            for i, file_path in enumerate(files_to_analyze, 1):
                if not self.analysis_running:
                    break
                    
                self.append_output(f"[{i}/{len(files_to_analyze)}] 🔍 Analyzing: {os.path.basename(file_path)}\n")
                
                # Read file content
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()[:5000]  # Limit content size
                except Exception as e:
                    self.append_output(f"❌ Error reading file: {e}\n\n")
                    continue
                
                # Create analysis prompt
                prompt = self.create_analysis_prompt(file_path, content, analysis_type)
                
                # Run Ollama analysis
                try:
                    self.current_process = subprocess.Popen(
                        ['ollama', 'run', model],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        env=env
                    )
                    
                    stdout, _ = self.current_process.communicate(input=prompt, timeout=180)
                    
                    if stdout:
                        # Clean up terminal control sequences
                        clean_output = self.clean_terminal_output(stdout)
                        if clean_output.strip():  # Only show if there's actual content
                            self.append_output(f"✅ Results for {os.path.basename(file_path)}:\n")
                            self.append_output("-" * 40 + "\n")
                            self.append_output(clean_output)
                            self.append_output("\n" + "=" * 50 + "\n\n")
                        else:
                            self.append_output(f"⚠️ No readable output from analysis of {os.path.basename(file_path)}\n\n")
                    
                except subprocess.TimeoutExpired:
                    self.append_output("⏱️ Analysis timed out for this file\n\n")
                    if self.current_process:
                        self.current_process.kill()
                except Exception as e:
                    self.append_output(f"❌ Error analyzing file: {e}\n\n")
            
            # Store analyzed files for potential fixing
            self.analyzed_files = files_to_analyze
            self.last_analysis_target = target
            self.last_analysis_type = analysis_type
            
            self.append_output("🎉 Analysis completed successfully!\n")
            self.append_output(f"📋 {len(files_to_analyze)} files analyzed and ready for fixing.\n")
            
        except Exception as e:
            self.append_output(f"\n❌ Analysis error: {e}\n")
        finally:
            self.root.after(0, self.analysis_finished)
    
    def create_analysis_prompt(self, file_path, content, analysis_type):
        """Create analysis prompt based on type"""
        file_ext = os.path.splitext(file_path)[1]
        language_map = {
            '.rs': 'Rust', '.ts': 'TypeScript', '.tsx': 'TypeScript', '.js': 'JavaScript', 
            '.jsx': 'JavaScript', '.py': 'Python', '.go': 'Go', '.java': 'Java',
            '.cpp': 'C++', '.c': 'C', '.h': 'C/C++'
        }
        language = language_map.get(file_ext, 'Unknown')
        
        base_prompt = f"Analyze this {language} code file: {os.path.basename(file_path)}\n\n{content}\n\n"
        
        if analysis_type == "cleanup":
            return base_prompt + """Please identify:
1. Stub functions (empty or placeholder implementations)
2. Unused functions, variables, and imports
3. Dead code that's never called
4. Commented-out code that should be removed
5. Redundant or duplicate code
6. Empty catch blocks or TODO comments

For each finding, specify line numbers and whether it's safe to remove."""
            
        elif analysis_type == "errors":
            return base_prompt + """Please identify:
1. Syntax errors
2. Type errors
3. Logic issues
4. Potential runtime errors
5. Missing imports or dependencies"""
            
        elif analysis_type == "security":
            return base_prompt + """Please identify:
1. Security vulnerabilities
2. Unsafe operations
3. Input validation issues
4. Authentication problems
5. Data exposure risks"""
            
        elif analysis_type == "performance":
            return base_prompt + """Please identify:
1. Performance bottlenecks
2. Inefficient algorithms
3. Memory usage issues
4. I/O optimization opportunities"""
            
        elif analysis_type == "style":
            return base_prompt + """Please review:
1. Code formatting and indentation
2. Naming conventions
3. Code organization
4. Documentation quality
5. Best practice compliance"""
            
        else:  # all
            return base_prompt + """Please provide comprehensive analysis covering:
1. Errors and bugs
2. Code style and best practices
3. Security considerations
4. Performance opportunities
5. Code cleanup (stub/unused code)"""
    
    def run_autofix_analysis(self):
        """Run analysis with auto-fix capability"""
        try:
            target = self.target_var.get().strip()
            model = self.model_var.get().replace('🚀 ', '').strip()
            analysis_type = self.analysis_var.get()
            
            self.append_output("🔧 Starting Ollama Auto-Fix Analysis\n")
            self.append_output("=" * 50 + "\n")
            self.append_output(f"📁 Target: {target}\n")
            self.append_output(f"🤖 Model: {model}\n")
            self.append_output(f"🔍 Analysis: {analysis_type}\n")
            self.append_output("⚠️  Auto-fix mode: Files will be modified!\n")
            self.append_output("=" * 50 + "\n\n")
            
            # Set environment
            env = os.environ.copy()
            env['OLLAMA_MODELS'] = self.models_path
            env['CUDA_VISIBLE_DEVICES'] = '0'  # Use GPU
            
            if os.path.isfile(target):
                files_to_analyze = [target]
            else:
                # Find code files in directory
                extensions = ['.rs', '.ts', '.tsx', '.js', '.jsx', '.py', '.go', '.java', '.cpp', '.c', '.h']
                files_to_analyze = []
                for root, dirs, files in os.walk(target):
                    # Skip common build/dependency directories
                    dirs[:] = [d for d in dirs if d not in ['node_modules', 'target', 'build', 'dist', '.git', '__pycache__']]
                    for file in files:
                        if any(file.endswith(ext) for ext in extensions):
                            file_path = os.path.join(root, file)
                            # Skip very large files (>50KB) for safety in auto-fix
                            try:
                                if os.path.getsize(file_path) < 50000:  # 50KB limit
                                    files_to_analyze.append(file_path)
                            except OSError:
                                pass  # Skip if can't get file size
            
            if not files_to_analyze:
                self.append_output("⚠️ No code files found to analyze.\n")
                return
            
            # Additional confirmation for large codebases in auto-fix mode
            if len(files_to_analyze) > 50:
                large_result = messagebox.askyesno(
                    "Large Codebase Warning", 
                    f"Found {len(files_to_analyze)} files to analyze and fix.\n\n"
                    f"This is a large codebase and processing may take a long time.\n\n"
                    f"⚠️ ALL {len(files_to_analyze)} FILES WILL BE MODIFIED!\n\n"
                    f"Are you sure you want to continue?"
                )
                if not large_result:
                    self.append_output("🛑 Auto-fix cancelled by user\n")
                    return
            
            self.append_output(f"📈 Found {len(files_to_analyze)} files to analyze and fix\n\n")
            
            fixed_files = 0
            
            for i, file_path in enumerate(files_to_analyze, 1):
                if not self.analysis_running:
                    break
                    
                self.append_output(f"[{i}/{len(files_to_analyze)}] 🔍 Analyzing: {os.path.basename(file_path)}\n")
                
                try:
                    # Read original file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        original_content = f.read()
                    
                    if len(original_content) > 10000:  # Skip very large files
                        self.append_output(f"⚠️ Skipping large file (>10k chars): {os.path.basename(file_path)}\n\n")
                        continue
                    
                    # Create fix prompt
                    prompt = self.create_fix_prompt(file_path, original_content, analysis_type)
                    
                    # Get fixed code from Ollama
                    self.current_process = subprocess.Popen(
                        ['ollama', 'run', model],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        env=env
                    )
                    
                    stdout, _ = self.current_process.communicate(input=prompt, timeout=180)
                    
                    if stdout:
                        # Clean up terminal control sequences first
                        clean_stdout = self.clean_terminal_output(stdout)
                        # Extract fixed code from AI response
                        fixed_code = self.extract_code_from_response(clean_stdout, original_content)
                        
                        if fixed_code and fixed_code != original_content:
                            # Create backup
                            backup_path = file_path + '.backup'
                            with open(backup_path, 'w', encoding='utf-8') as f:
                                f.write(original_content)
                            
                            # Write fixed code
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(fixed_code)
                            
                            self.append_output(f"✅ Fixed: {os.path.basename(file_path)} (backup created)\n")
                            fixed_files += 1
                        else:
                            self.append_output(f"ℹ️ No fixes needed: {os.path.basename(file_path)}\n")
                    
                except subprocess.TimeoutExpired:
                    self.append_output(f"⏱️ Timeout analyzing: {os.path.basename(file_path)}\n")
                    if self.current_process:
                        self.current_process.kill()
                except Exception as e:
                    self.append_output(f"❌ Error processing {os.path.basename(file_path)}: {str(e)}\n")
                
                self.append_output("\n")
            
            self.append_output("=" * 50 + "\n")
            self.append_output(f"🎉 Auto-fix complete! Fixed {fixed_files}/{len(files_to_analyze)} files\n")
            self.append_output("💾 Backup files created with .backup extension\n")
            
        except Exception as e:
            self.append_output(f"\n❌ Auto-fix error: {e}\n")
        finally:
            self.root.after(0, self.analysis_finished)
    
    def create_fix_prompt(self, file_path, content, analysis_type):
        """Create prompt for fixing code"""
        file_ext = os.path.splitext(file_path)[1]
        language_map = {
            '.rs': 'Rust', '.ts': 'TypeScript', '.tsx': 'TypeScript', '.js': 'JavaScript', 
            '.jsx': 'JavaScript', '.py': 'Python', '.go': 'Go', '.java': 'Java',
            '.cpp': 'C++', '.c': 'C', '.h': 'C/C++'
        }
        language = language_map.get(file_ext, 'Unknown')
        
        base_prompt = f"""Fix the issues in this {language} code file: {os.path.basename(file_path)}

Original code:
```{language.lower()}
{content}
```

Please:
1. Identify and fix any errors, bugs, or issues
2. Remove unused imports, variables, and functions
3. Remove commented-out code
4. Fix code style issues
5. Improve performance where possible

Return ONLY the fixed code wrapped in ```{language.lower()} code blocks. Do not include explanations or other text."""
        
        return base_prompt
    
    def clean_terminal_output(self, text):
        """Remove terminal control sequences and formatting codes from text"""
        import re
        
        # Remove ANSI escape sequences (colors, cursor movement, etc.)
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        text = ansi_escape.sub('', text)
        
        # Remove specific terminal control sequences
        control_sequences = [
            r'\[\?\d+[hl]',  # Private mode sequences
            r'\[\d*[ABCD]',  # Cursor movement
            r'\[\d*[GKJ]',   # Erase sequences
            r'\[\d+;\d+[Hf]', # Cursor position
            r'\[\?25[lh]',   # Cursor visibility
            r'\[\?2026[hl]', # Bracketed paste mode
            r'\[2K',         # Clear line
            r'\[1G',         # Move to column 1
            r'\[K',          # Clear to end of line
        ]
        
        for pattern in control_sequences:
            text = re.sub(pattern, '', text)
        
        # Remove spinner characters and extra whitespace
        spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        for char in spinner_chars:
            text = text.replace(char, '')
        
        # Clean up excessive whitespace and newlines
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Multiple newlines to double
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single
        text = text.strip()
        
        return text
    
    def detect_dominant_language(self, target_path):
        """Detect the dominant programming language in target"""
        if not os.path.exists(target_path):
            return None
        
        language_counts = {}
        extensions = ['.rs', '.ts', '.tsx', '.js', '.jsx', '.py', '.go', '.java', '.cpp', '.c', '.h']
        
        if os.path.isfile(target_path):
            ext = os.path.splitext(target_path)[1]
            if ext in extensions:
                return self.get_language_from_extension(ext)
            return None
        
        # Count files by language
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in ['node_modules', 'target', 'build', 'dist', '.git']]
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in extensions:
                    lang = self.get_language_from_extension(ext)
                    language_counts[lang] = language_counts.get(lang, 0) + 1
        
        if not language_counts:
            return None
        
        # Return most common language
        return max(language_counts, key=language_counts.get)
    
    def get_language_from_extension(self, ext):
        """Map file extension to language name"""
        ext_map = {
            '.rs': 'rust',
            '.ts': 'typescript', '.tsx': 'typescript',
            '.js': 'javascript', '.jsx': 'javascript',
            '.py': 'python',
            '.go': 'go',
            '.java': 'java',
            '.cpp': 'cpp', '.c': 'c', '.h': 'c'
        }
        return ext_map.get(ext, 'general')
    
    def get_best_model_for_language(self, language):
        """Get the best available model for a specific language"""
        available_models = self.model_combo['values']
        
        # Model preferences by language
        language_models = {
            'rust': ['granite-code', 'deepseek-coder', 'codellama'],
            'typescript': ['granite-code', 'deepseek-coder', 'codegemma'],
            'javascript': ['granite-code', 'deepseek-coder', 'codegemma'],
            'python': ['deepseek-coder', 'granite-code', 'codellama'],
            'go': ['granite-code', 'deepseek-coder', 'codellama'],
            'java': ['granite-code', 'deepseek-coder', 'codellama'],
            'cpp': ['granite-code', 'deepseek-coder', 'codellama'],
            'c': ['granite-code', 'deepseek-coder', 'codellama']
        }
        
        preferred_models = language_models.get(language, ['granite-code', 'deepseek-coder'])
        
        # Find best available model
        for preferred in preferred_models:
            for model in available_models:
                if preferred in model.lower():
                    return model
        
        # Fallback to first code model
        for model in available_models:
            if '🚀' in model:
                return model
        
        return available_models[0] if available_models else 'granite-code:latest'
    
    def auto_select_model(self):
        """Automatically select best model for the target code"""
        target = self.target_var.get().strip()
        if not target:
            return
        
        language = self.detect_dominant_language(target)
        if language:
            best_model = self.get_best_model_for_language(language)
            self.model_var.set(best_model)
            self.status_var.set(f"Auto-selected {best_model} for {language.title()} code")
        else:
            self.status_var.set("Could not detect code language for auto-selection")
    
    def on_target_change(self, *args):
        """Called when target path changes"""
        # Auto-suggest after a short delay to avoid constant updates while typing
        if hasattr(self, '_target_timer'):
            self.root.after_cancel(self._target_timer)
        self._target_timer = self.root.after(1000, self.auto_select_model)
    
    def load_previous_results(self):
        """Load previous analysis results from file"""
        file_path = filedialog.askopenfilename(
            title="Load Previous Analysis Results",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.clear_output()
                self.append_output(f"📂 Loaded results from: {os.path.basename(file_path)}\n")
                self.append_output("=" * 50 + "\n")
                self.append_output(content)
                
                # Try to extract analyzed files from the report
                self.extract_analyzed_files_from_report(content, os.path.dirname(file_path))
                
                if self.analyzed_files:
                    self.fix_button.config(state=tk.NORMAL)
                    self.status_var.set(f"Loaded results - {len(self.analyzed_files)} files ready for fixing")
                else:
                    self.status_var.set("Results loaded - No fixable files detected")
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not load file: {e}")
    
    def extract_analyzed_files_from_report(self, content, base_dir):
        """Extract file paths from analysis report"""
        import re
        self.analyzed_files = []
        
        # Look for file patterns in the report
        file_patterns = [
            r'Results for ([^:\n]+):',
            r'Analyzing: ([^\n]+)',
            r'Fixed: ([^\n]+)',
            r'File: ([^\n]+)'
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Clean up the filename
                filename = match.strip()
                if filename and not filename.startswith('/'):
                    full_path = os.path.join(base_dir, filename)
                    if os.path.exists(full_path) and full_path not in self.analyzed_files:
                        self.analyzed_files.append(full_path)
    
    def start_fix_only(self):
        """Start fix-only mode for previously analyzed files"""
        if not self.analyzed_files:
            messagebox.showwarning("No Files", "No analyzed files available for fixing.\nRun analysis first or load previous results.")
            return
        
        if self.analysis_running:
            return
        
        # Confirm fix action
        result = messagebox.askyesno(
            "Fix Issues Confirmation", 
            f"This will apply fixes to {len(self.analyzed_files)} previously analyzed files.\n\n"
            "⚠️ IMPORTANT: This will modify your files!\n\n"
            "Make sure you have backups or are using version control.\n\n"
            "Do you want to continue?"
        )
        
        if not result:
            return
        
        # Clean model name
        model = self.model_var.get().replace('🚀 ', '').strip()
        
        self.analysis_running = True
        self.analyze_button.config(state=tk.DISABLED)
        self.fix_button.config(state=tk.DISABLED)
        self.autofix_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress.start()
        self.status_var.set("Applying fixes to analyzed files...")
        
        # Clear previous output
        self.clear_output()
        
        # Run fix in separate thread
        thread = threading.Thread(target=self.run_fix_only)
        thread.daemon = True
        thread.start()
    
    def run_fix_only(self):
        """Run fixes on previously analyzed files"""
        try:
            model = self.model_var.get().replace('🚀 ', '').strip()
            
            self.append_output("🔧 Starting Fix-Only Mode\n")
            self.append_output("=" * 50 + "\n")
            self.append_output(f"🤖 Model: {model}\n")
            self.append_output(f"📁 Files to fix: {len(self.analyzed_files)}\n")
            self.append_output("⚠️  Fix mode: Files will be modified!\n")
            self.append_output("=" * 50 + "\n\n")
            
            # Set environment
            env = os.environ.copy()
            env['OLLAMA_MODELS'] = self.models_path
            env['CUDA_VISIBLE_DEVICES'] = '0'
            
            fixed_files = 0
            
            for i, file_path in enumerate(self.analyzed_files, 1):
                if not self.analysis_running:
                    break
                
                if not os.path.exists(file_path):
                    self.append_output(f"⚠️ Skipping missing file: {os.path.basename(file_path)}\n")
                    continue
                    
                self.append_output(f"[{i}/{len(self.analyzed_files)}] 🔍 Fixing: {os.path.basename(file_path)}\n")
                
                try:
                    # Read original file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        original_content = f.read()
                    
                    if len(original_content) > 10000:  # Skip very large files
                        self.append_output(f"⚠️ Skipping large file: {os.path.basename(file_path)}\n\n")
                        continue
                    
                    # Create fix prompt
                    prompt = self.create_fix_prompt(file_path, original_content, 'cleanup')
                    
                    # Get fixed code from Ollama
                    self.current_process = subprocess.Popen(
                        ['ollama', 'run', model],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        env=env
                    )
                    
                    stdout, _ = self.current_process.communicate(input=prompt, timeout=180)
                    
                    if stdout:
                        # Clean up terminal control sequences first
                        clean_stdout = self.clean_terminal_output(stdout)
                        # Extract fixed code from AI response
                        fixed_code = self.extract_code_from_response(clean_stdout, original_content)
                        
                        if fixed_code and fixed_code != original_content:
                            # Create backup
                            backup_path = file_path + '.backup'
                            with open(backup_path, 'w', encoding='utf-8') as f:
                                f.write(original_content)
                            
                            # Write fixed code
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(fixed_code)
                            
                            self.append_output(f"✅ Fixed: {os.path.basename(file_path)} (backup created)\n")
                            fixed_files += 1
                        else:
                            self.append_output(f"ℹ️ No fixes needed: {os.path.basename(file_path)}\n")
                    
                except subprocess.TimeoutExpired:
                    self.append_output(f"⏱️ Timeout fixing: {os.path.basename(file_path)}\n")
                    if self.current_process:
                        self.current_process.kill()
                except Exception as e:
                    self.append_output(f"❌ Error fixing {os.path.basename(file_path)}: {str(e)}\n")
                
                self.append_output("\n")
            
            self.append_output("=" * 50 + "\n")
            self.append_output(f"🎉 Fix-only complete! Fixed {fixed_files}/{len(self.analyzed_files)} files\n")
            self.append_output("💾 Backup files created with .backup extension\n")
            
        except Exception as e:
            self.append_output(f"\n❌ Fix-only error: {e}\n")
        finally:
            self.root.after(0, self.analysis_finished)
    
    def extract_code_from_response(self, response, original_content):
        """Extract code from AI response"""
        import re
        
        # Look for code blocks
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
        
        if code_blocks:
            # Use the largest code block
            fixed_code = max(code_blocks, key=len).strip()
            
            # Basic validation - should be similar length and have some common elements
            if len(fixed_code) > len(original_content) * 0.5 and len(fixed_code) < len(original_content) * 2:
                return fixed_code
        
        return None
    
    def analysis_finished(self):
        """Called when analysis is complete"""
        self.analysis_running = False
        self.analyze_button.config(state=tk.NORMAL)
        self.autofix_button.config(state=tk.NORMAL)
        
        # Enable Fix button only if we have analyzed files
        if self.analyzed_files:
            self.fix_button.config(state=tk.NORMAL)
            self.status_var.set(f"Analysis complete - {len(self.analyzed_files)} files analyzed. Click 'Fix Issues' to apply fixes.")
        else:
            self.fix_button.config(state=tk.DISABLED)
            self.status_var.set("Analysis complete - Ready for new analysis")
        
        self.stop_button.config(state=tk.DISABLED)
        self.progress.stop()
        self.current_process = None

def main():
    root = tk.Tk()
    app = OllamaCodeCheckerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()