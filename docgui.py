import sys
import os
from pathlib import Path
import webbrowser
import subprocess
import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

def install_required_packages():
    required = {
        'gitpython': 'git'
        # 'pathlib': 'pathlib'  # Removed pathlib as it's included in the standard library
    }
    
    # Check tkinter first (already imported above)
    def pip_install(package):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            return True
        except subprocess.CalledProcessError:
            return False

    for package, import_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            print(f"Installing {package}...")
            if not pip_install(package):
                print(f"Failed to install {package}")
                sys.exit(1)

# Initialize required packages before git import
install_required_packages()

# Now import git after ensuring it's installed
import git

# Setup logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler(sys.stdout)])

def show_git_install_prompt():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    result = messagebox.askquestion(
        "Git Not Found",
        "Git is required but not found on your system. Would you like to download and install Git?",
        icon='question'
    )
    if result == 'yes':
        webbrowser.open('https://git-scm.com/downloads')
    root.destroy()
    return result == 'yes'

def find_git_executable():
    possible_paths = [
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\bin\git.exe",
        r"C:\Git\bin\git.exe"
    ]
    
    # Check if git is in PATH
    try:
        import subprocess
        result = subprocess.run(['where', 'git'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        pass
        
    # Check common installation paths
    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    # Show GUI prompt for Git installation
    if show_git_install_prompt():
        sys.exit(0)  # Exit gracefully after opening browser
    else:
        sys.exit(1)  # Exit if user declines installation

try:
    # Find and configure git executable
    git_exe = find_git_executable()
    if (git_exe is None):
        print("Git executable not found. Please install Git from https://git-scm.com/downloads")
        sys.exit(1)
    
    os.environ['GIT_PYTHON_GIT_EXECUTABLE'] = git_exe
    
except ImportError as e:
    if 'git' in str(e):
        print("GitPython package is not installed.")
        print("Please run: pip install gitpython")
        sys.exit(1)
    raise e
except Exception as e:
    print(f"Error initializing git: {str(e)}")
    print("Please ensure Git is installed and available in the system PATH")
    print(f"Or set the correct path to git.exe in the script")
    sys.exit(1)

def verify_node():
    try:
        result = subprocess.run('node --version', shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

class ConsoleRedirector:
    def __init__(self, text_widget, tag):
        self.text_widget = text_widget
        self.tag = tag

    def write(self, text):
        self.text_widget.insert(tk.END, text, self.tag)
        self.text_widget.see(tk.END)
        self.text_widget.update()

    def flush(self):
        pass

class DocusaurusDeployGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Docusaurus Site Builder & Deployment Tool")
        self.root.geometry("800x600")
        
        # Project directory
        tk.Label(root, text="Select Target Directory:").pack(pady=10)
        self.dir_frame = tk.Frame(root)
        self.dir_frame.pack(fill=tk.X, padx=20)
        self.dir_entry = tk.Entry(self.dir_frame)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(self.dir_frame, text="Browse", command=self.browse_directory).pack(side=tk.RIGHT, padx=5)

        # Site name
        tk.Label(root, text="Site Name:").pack(pady=10)
        self.site_name = tk.Entry(root, width=50)
        self.site_name.pack()

        # GitHub repository URL
        tk.Label(root, text="GitHub Repository URL:").pack(pady=10)
        self.repo_entry = tk.Entry(root, width=50)
        self.repo_entry.pack()
        self.repo_entry.insert(0, "")  # Set default to empty

        # Branch name
        tk.Label(root, text="Branch name (default: main):").pack(pady=10)
        self.branch_entry = tk.Entry(root, width=50)
        self.branch_entry.insert(0, "main")
        self.branch_entry.pack()

        # Remove GitHub Username field

        # Buttons frame
        self.buttons_frame = tk.Frame(root)
        self.buttons_frame.pack(pady=20)
        
        tk.Button(self.buttons_frame, text="Initialize Site", command=self.initialize_site).pack(side=tk.LEFT, padx=5)
        tk.Button(self.buttons_frame, text="Deploy to GitHub Pages", command=self.deploy).pack(side=tk.LEFT, padx=5)

        # Status
        self.status_label = tk.Label(root, text="")
        self.status_label.pack(pady=10)

        # Add console output
        tk.Label(root, text="Console Output:").pack(pady=5)
        self.console = scrolledtext.ScrolledText(root, height=10)
        self.console.pack(padx=20, pady=5, fill=tk.BOTH, expand=True)
        
        # Configure console with colors
        self.console.tag_configure("error", foreground="red")
        self.console.tag_configure("normal", foreground="black")
        
        # Redirect stdout and stderr
        sys.stdout = ConsoleRedirector(self.console, "normal")
        sys.stderr = ConsoleRedirector(self.console, "error")
        
        self.is_busy = False

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)

    def verify_environment(self):
        if not verify_node():
            self.console.insert(tk.END, "Node.js is not installed. Please install Node.js from https://nodejs.org\n", "error")
            webbrowser.open('https://nodejs.org')
            return False
            
        try:
            # Pre-install required npm packages globally
            self.console.insert(tk.END, "Checking/installing required npm packages...\n", "normal")
            subprocess.run('npm install -g create-docusaurus@latest', 
                         shell=True, 
                         check=True,
                         capture_output=True)
            
            # Rest of environment checks
            npm_check = subprocess.run('npm --version', 
                                    shell=True, 
                                    capture_output=True, 
                                    text=True)
            git_check = subprocess.run('git --version', 
                                     shell=True, 
                                     capture_output=True, 
                                     text=True)
            
            if npm_check.returncode != 0:
                self.console.insert(tk.END, f"npm check failed: {npm_check.stderr}\n", "error")
                return False
            if git_check.returncode != 0:
                self.console.insert(tk.END, f"git check failed: {git_check.stderr}\n", "error")
                return False
                
            self.console.insert(tk.END, f"npm version: {npm_check.stdout}", "normal")
            self.console.insert(tk.END, f"git version: {git_check.stdout}", "normal")
            return True
            
        except Exception as e:
            self.console.insert(tk.END, f"Environment check error: {str(e)}\n", "error")
            return False

    def run_async(self, func):
        if self.is_busy:
            messagebox.showwarning("Busy", "An operation is already in progress")
            return
        self.is_busy = True
        self.status_label.config(text="Working...")
        
        def wrapper():
            try:
                func()
            finally:
                self.is_busy = False
                self.root.after(100, lambda: self.status_label.config(text="Ready"))
        
        thread = threading.Thread(target=wrapper)
        thread.daemon = True
        thread.start()

    def initialize_site(self):
        self.run_async(self._initialize_site)
        
    def deploy(self):
        self.run_async(lambda: self._deploy(branch='gh-pages'))

    def _initialize_site(self):
        try:
            if not self.verify_environment():
                return

            project_dir = self.dir_entry.get()
            site_name = self.site_name.get()

            if not all([project_dir, site_name]):
                raise ValueError("Directory and site name are required!")

            self.status_label.config(text="Creating Docusaurus site...")
            self.console.insert(tk.END, "Starting site creation...\n", "normal")
            
            # Create Docusaurus project with live output using npx without prompts
            create_command = 'npx --yes create-docusaurus@latest'
            args = [site_name, 'classic', '--typescript']
            
            process = subprocess.Popen(
                f'{create_command} {" ".join(args)}',
                shell=True,
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True
            )

            # Monitor process output in real-time
            while True:
                output = process.stdout.readline()
                if output:
                    self.console.insert(tk.END, output, "normal")
                    self.console.see(tk.END)
                    self.console.update()
                    
                error = process.stderr.readline()
                if error:
                    self.console.insert(tk.END, error, "error")
                    self.console.see(tk.END)
                    self.console.update()
                
                # Check if process has finished
                if process.poll() is not None:
                    break
                    
            if process.returncode != 0:
                raise ValueError("Failed to create Docusaurus site")

            # Continue with rest of initialization...
            full_project_path = os.path.abspath(os.path.join(project_dir, site_name))
            if not os.path.exists(full_project_path):
                raise ValueError(f"Site directory was not created at {full_project_path}")
            
            self.console.insert(tk.END, "Site directory created successfully.\n", "normal")
            
            # Update directory to the new project folder
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, full_project_path)

            # Install dependencies
            self.status_label.config(text="Installing dependencies...")
            install_result = subprocess.run('npm install',
                                         shell=True,
                                         cwd=full_project_path,
                                         capture_output=True,
                                         text=True)
            
            if install_result.returncode != 0:
                raise ValueError("Failed to install dependencies")

            self.status_label.config(text="Site initialized successfully!")
            messagebox.showinfo("Success", "Docusaurus site created successfully!")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.console.insert(tk.END, f"Initialization error: {str(e)}\n", "error")
            self.status_label.config(text=error_msg)
            messagebox.showerror("Error", error_msg)

    def _deploy(self, branch='gh-pages'):
        try:
            # Define env early to ensure it's available for subprocess calls
            env = os.environ.copy()
            env['USE_SSH'] = 'true'

            project_dir = self.dir_entry.get()
            project_dir = os.path.abspath(project_dir)  # Ensure absolute path

            if not os.path.exists(project_dir):
                error_msg = f"Project directory does not exist: {project_dir}"
                logging.error(error_msg)
                self.console.insert(tk.END, f"{error_msg}\n", "error")
                return

            # Verify Docusaurus project
            config_files = ['docusaurus.config.js', 'docusaurus.config.ts']
            config_found = False
            for config_file in config_files:
                config_path = os.path.join(project_dir, config_file)
                if os.path.exists(config_path):
                    config_found = True
                    break  # Found the configuration file

            if not config_found:
                error_msg = (f"Invalid Docusaurus project directory! Cannot find "
                             f"'docusaurus.config.js' or 'docusaurus.config.ts' in {project_dir}")
                logging.error(error_msg)
                self.console.insert(tk.END, f"{error_msg}\n", "error")
                if messagebox.askyesno("Site Not Initialized",
                                       "Docusaurus site not found. Do you want to initialize it first?"):
                    self.initialize_site()
                return

            if not self.verify_environment():
                return

            repo_url = self.repo_entry.get().strip()
            branch = self.branch_entry.get().strip()

            # Validate the GitHub Repository URL
            if not repo_url:
                error_msg = "GitHub Repository URL cannot be empty."
                logging.error(error_msg)
                self.console.insert(tk.END, f"{error_msg}\n", "error")
                messagebox.showerror("Invalid Repository URL", error_msg)
                return
            if repo_url == "git@github.com:facebook/docusaurus.git":
                error_msg = "Please update the GitHub Repository URL to your own repository."
                logging.error(error_msg)
                self.console.insert(tk.END, f"{error_msg}\n", "error")
                messagebox.showerror("Invalid Repository URL", error_msg)
                return

            # Ensure .ssh directory exists and add GitHub to known_hosts
            ssh_dir = os.path.join(os.environ.get('USERPROFILE', ''), '.ssh')
            os.makedirs(ssh_dir, exist_ok=True)

            ssh_scan_result = subprocess.run(
                ['ssh-keyscan', 'github.com'],
                capture_output=True,
                text=True,
                env=env
            )
            if ssh_scan_result.returncode == 0:
                known_hosts_path = os.path.join(ssh_dir, 'known_hosts')
                with open(known_hosts_path, 'a') as f:
                    f.write(ssh_scan_result.stdout)
            else:
                self.console.insert(tk.END, f"Error running ssh-keyscan: {ssh_scan_result.stderr}\n", "error")
                logging.error(f"ssh-keyscan failed: {ssh_scan_result.stderr}")

            logging.info(f"Starting deployment from {project_dir}")
            logging.info(f"Repository URL: {repo_url}")
            logging.info(f"Branch: {branch}")

            if not all([repo_url, branch]):
                raise ValueError("Repository URL and branch name are required!")

            # Verify Docusaurus project
            config_files = ['docusaurus.config.js', 'docusaurus.config.ts']
            config_found = False
            for config_file in config_files:
                config_path = os.path.join(project_dir, config_file)
                if os.path.exists(config_path):
                    config_found = True
                    break  # Found the configuration file

            if not config_found:
                error_msg = f"Invalid Docusaurus project directory! Cannot find 'docusaurus.config.js' or 'docusaurus.config.ts' in {project_dir}"
                logging.error(error_msg)
                self.console.insert(tk.END, f"{error_msg}\n", "error")
                raise ValueError(error_msg)

            # Initialize git if needed
            if not os.path.exists(os.path.join(project_dir, '.git')):
                logging.info("Initializing new git repository...")
                repo = git.Repo.init(project_dir, initial_branch=branch)
                # Create an initial commit to avoid empty branch issues
                repo.git.add(all=True)
                repo.index.commit('Initial commit')
            else:
                logging.info("Using existing git repository...")
                repo = git.Repo(project_dir)
                # Check if the branch exists
                if branch in repo.heads:
                    repo.git.checkout(branch)
                else:
                    # Create and switch to the new branch
                    repo.git.checkout('-b', branch)

            # Build the project
            self.status_label.config(text="Building project...")
            logging.info("Running npm run build...")
            result = subprocess.run('npm run build', 
                                 shell=True,
                                 cwd=project_dir, 
                                 capture_output=True,
                                 text=True)
            
            self.console.insert(tk.END, result.stdout, "normal")
            if result.stderr:
                self.console.insert(tk.END, result.stderr, "error")

            if result.returncode != 0:
                raise ValueError(f"Build failed:\n{result.stderr}")
            
            # Configure git
            if 'origin' not in [remote.name for remote in repo.remotes]:
                logging.info("Adding remote origin...")
                repo.create_remote('origin', repo_url)

            # Add and commit changes
            logging.info("Committing changes...")
            repo.git.add(all=True)
            try:
                repo.git.commit('-m', 'Deploy to GitHub Pages')
            except git.exc.GitCommandError as e:
                if 'nothing to commit' in str(e):
                    logging.info("No changes to commit")
                else:
                    raise

            # Push to GitHub
            self.status_label.config(text="Pushing to GitHub...")
            logging.info("Pushing to GitHub...")
            push_result = subprocess.run(
                ['git', 'push', '--set-upstream', 'origin', branch],
                capture_output=True,
                text=True,
                cwd=project_dir,
                env=env
            )

            if push_result.returncode != 0:
                if 'Permission denied (publickey)' in push_result.stderr:
                    self.console.insert(tk.END, "SSH Authentication failed. Please ensure your SSH keys are properly set up and added to GitHub.\n", "error")
                    logging.error("SSH Authentication failed. Please ensure your SSH keys are properly set up and added to GitHub.")
                else:
                    self.console.insert(tk.END, f"Git push failed: {push_result.stderr}\n", "error")
                    logging.error(f"Git push failed: {push_result.stderr}")
                raise ValueError(f"Git push failed:\n{push_result.stderr}")

            # Ensure .ssh directory exists
            ssh_dir = os.path.join(os.environ.get('USERPROFILE', ''), '.ssh')
            os.makedirs(ssh_dir, exist_ok=True)

            # Add GitHub to known_hosts to prevent Host key verification failure
            ssh_scan_result = subprocess.run(
                ['ssh-keyscan', 'github.com'],
                capture_output=True,
                text=True,
                env=env
            )
            if ssh_scan_result.returncode == 0:
                known_hosts_path = os.path.join(ssh_dir, 'known_hosts')
                with open(known_hosts_path, 'a') as f:
                    f.write(ssh_scan_result.stdout)
            else:
                self.console.insert(tk.END, f"Error running ssh-keyscan: {ssh_scan_result.stderr}\n", "error")
                logging.error(f"ssh-keyscan failed: {ssh_scan_result.stderr}")

            # Deploy to GitHub Pages - let SSH handle authentication
            logging.info("Running npm run deploy...")
            deploy_result = subprocess.run(
                'npm run deploy',
                shell=True,
                cwd=project_dir,
                capture_output=True,
                text=True,
                env=env
            )

            self.console.insert(tk.END, deploy_result.stdout, "normal")
            if deploy_result.stderr:
                self.console.insert(tk.END, deploy_result.stderr, "error")

            if deploy_result.returncode != 0:
                raise ValueError(f"Deploy failed:\n{deploy_result.stderr}")

            self.status_label.config(text="Deployment successful!")
            messagebox.showinfo("Success", "Deployed to GitHub Pages successfully!")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logging.error(error_msg)
            self.console.insert(tk.END, f"Deployment error: {str(e)}\n", "error")
            self.status_label.config(text=error_msg)
            messagebox.showerror("Error", error_msg)
            raise  # Re-raise to see full traceback in console

    def update_console(self, text, tag="normal"):
        self.root.after(0, lambda: self.console.insert(tk.END, text, tag))
        self.root.after(0, lambda: self.console.see(tk.END))

if __name__ == "__main__":
    root = tk.Tk()
    app = DocusaurusDeployGUI(root)
    root.mainloop()
