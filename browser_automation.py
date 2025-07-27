import subprocess
import sys
import os

def install_and_import_psutil():
    """Install psutil if not available, then import it"""
    try:
        import psutil
        return psutil
    except ImportError:
        print("🔧 psutil not found, installing automatically...")
        try:
            # Try different pip commands
            commands = [
                [sys.executable, "-m", "pip", "install", "psutil"],
                ["pip3", "install", "psutil"],
                ["pip", "install", "psutil"]
            ]
            
            for cmd in commands:
                try:
                    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print("✅ psutil installed successfully!")
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            
            # Try to import again after installation
            import psutil
            return psutil
        except Exception as e:
            print(f"❌ Failed to install psutil: {e}")
            print("📋 Continuing without psutil - using fallback memory detection")
            return None

# Install and import psutil
psutil = install_and_import_psutil()

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from cog import BasePredictor, Input, Path
import time
import gc
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
import random
import tempfile


class Predictor(BasePredictor):
    def setup(self) -> None:
        """Load the model into memory to make running multiple predictions efficient"""
        self.browsers = []
        self.running = False
        self.max_memory_percent = 98
        self.browser_lock = threading.Lock()
        self.cache_dir = tempfile.mkdtemp()
        self.cpu_count = multiprocessing.cpu_count()
        self.max_concurrent_browsers = min(self.cpu_count * 16, 256)  # Maximized for GPU
        self.psutil_available = psutil is not None
        
        # Pre-configure Chrome options for maximum performance
        self.base_options = self._create_maximized_chrome_options()
        
        print(f"🚀 GPU POWER MODE: {self.cpu_count} CPU cores, up to {self.max_concurrent_browsers} concurrent browsers")
        if self.psutil_available:
            print("✅ psutil available - using accurate memory monitoring")
        else:
            print("⚠️ psutil not available - using fallback memory detection")


    def _create_maximized_chrome_options(self):
        """Create maximum performance Chrome options that still load content properly"""
        options = webdriver.ChromeOptions()
        
        # Core performance flags
        options.binary_location = '/usr/bin/google-chrome-stable'
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-fonts')
        
        # Performance optimizations
        options.add_argument('--disable-logging')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-translate')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-hang-monitor')
        options.add_argument('--disable-prompt-on-repost')
        options.add_argument('--disable-client-side-phishing-detection')
        options.add_argument('--disable-component-update')
        options.add_argument('--disable-domain-reliability')
        options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees')
        options.add_argument('--disable-ipc-flooding-protection')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Memory optimizations
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        options.add_argument('--aggressive-cache-discard')
        options.add_argument('--disable-background-mode')
        options.add_argument('--disable-features=MediaRouter')
        options.add_argument('--disable-print-preview')
        options.add_argument('--disable-speech-api')
        options.add_argument('--disable-file-system')
        options.add_argument('--disable-databases')
        
        # Network optimizations
        options.add_argument('--aggressive-tab-discard')
        options.add_argument('--disable-background-sync')
        options.add_argument('--disable-permissions-api')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-geolocation')
        
        # Cache optimization
        options.add_argument(f'--disk-cache-dir={self.cache_dir}')
        options.add_argument('--disk-cache-size=2147483648')
        options.add_argument('--media-cache-size=2147483648')
        
        # GPU optimizations
        options.add_argument('--disable-gpu-sandbox')
        options.add_argument('--ignore-gpu-blacklist')
        options.add_argument('--enable-gpu-rasterization')
        options.add_argument('--disable-software-rasterizer')
        
        # Video-friendly performance flags
        options.add_argument('--disable-features=AudioServiceOutOfProcess')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-component-extensions-with-background-pages')
        options.add_argument('--disable-extensions-file-access-check')
        options.add_argument('--disable-extensions-http-throttling')
        
        # Autoplay policies for video
        options.add_argument('--autoplay-policy=no-user-gesture-required')
        options.add_argument('--disable-features=PreloadMediaEngagementData,AutoplayIgnoreWebAudio,MediaEngagementBypassAutoplayPolicies')
        options.add_argument('--disable-background-media-suspend')
        options.add_argument('--disable-low-res-tiling')
        
        # Experimental optimizations
        options.add_experimental_option("detach", True)
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        
        # Performance preferences
        prefs = {
            'profile.default_content_setting_values': {
                'notifications': 2,
                'geolocation': 2,
                'plugins': 2,
                'popups': 2,
                'automatic_downloads': 2,
                'cookies': 1,
                'javascript': 1,
                'images': 1,
                'media_stream': 1,
                'microphone': 2,
                'camera': 2,
            },
            'profile.managed_default_content_settings': {
                'plugins': 2,
                'popups': 2,
                'geolocation': 2,
                'notifications': 2,
            },
            'profile.content_settings.exceptions.media_stream': {},
            'profile.content_settings.exceptions.clipboard': {},
            'profile.content_settings.exceptions.notification': {},
        }
        options.add_experimental_option('prefs', prefs)
        
        # Use eager page load strategy
        options.page_load_strategy = 'eager'
        
        return options


    def get_memory_usage(self):
        """Get current memory usage percentage with multiple fallbacks"""
        if self.psutil_available and psutil:
            try:
                memory = psutil.virtual_memory()
                return round(memory.percent, 1)
            except:
                pass
        
        # Fallback 1: /proc/meminfo
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
            
            mem_total = None
            mem_available = None
            
            for line in lines:
                if line.startswith('MemTotal:'):
                    mem_total = int(line.split()[1])
                elif line.startswith('MemAvailable:'):
                    mem_available = int(line.split()[1])
            
            if mem_total and mem_available:
                used_percent = ((mem_total - mem_available) / mem_total) * 100
                return round(used_percent, 1)
        except:
            pass
        
        # Fallback 2: free command
        try:
            result = subprocess.run(['free', '-m'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            mem_line = lines[1].split()
            total = int(mem_line[1])
            available = int(mem_line[6]) if len(mem_line) > 6 else int(mem_line[3])
            used_percent = ((total - available) / total) * 100
            return round(used_percent, 1)
        except:
            pass
        
        # Final fallback
        return 70.0


    def create_browser_ultra_fast(self, url, window_id):
        """Create browser with maximum speed while loading content"""
        browser = None
        try:
            # Clone optimized options
            options = webdriver.ChromeOptions()
            for arg in self.base_options.arguments:
                options.add_argument(arg)
            
            for key, value in self.base_options.experimental_options.items():
                options.add_experimental_option(key, value)
            
            # Set page load strategy to eager
            options.page_load_strategy = 'eager'
            
            # Add unique cache directory
            unique_cache = os.path.join(self.cache_dir, f'browser_{window_id}')
            os.makedirs(unique_cache, exist_ok=True)
            options.add_argument(f'--user-data-dir={unique_cache}')
            
            # Create service
            service = Service()
            
            # Create browser with fast timeouts
            browser = webdriver.Chrome(service=service, options=options)
            browser.set_page_load_timeout(20)  # Reduced timeout
            browser.implicitly_wait(3)  # Reduced wait
            
            # Load page quickly
            browser.get(url)
            
            # Quick content verification
            time.sleep(1.5)  # Reduced wait time
            
            # Try to start video quickly
            try:
                # Quick video interaction
                browser.execute_script("""
                    var videos = document.querySelectorAll('video');
                    videos.forEach(function(video) {
                        try { video.play(); } catch(e) {}
                    });
                    // Quick page interaction
                    document.body.click();
                """)
            except:
                pass
            
            # Keep browser active
            try:
                browser.execute_script("window.ultraFastActive = true;")
            except:
                pass
            
            with self.browser_lock:
                self.browsers.append(browser)
                current_count = len(self.browsers)
            
            print(f"⚡ Window {window_id} loaded ultra-fast (Total: {current_count})")
            return browser
            
        except Exception as e:
            print(f"❌ Failed to create window {window_id}: {str(e)}")
            if browser:
                try:
                    browser.quit()
                except:
                    pass
            return None


    def gpu_batch_create(self, url, start_idx, batch_size):
        """GPU-optimized batch creation with maximum concurrency"""
        successful_browsers = []
        
        # Use maximum threads for GPU system
        max_workers = min(batch_size, self.max_concurrent_browsers)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self.create_browser_ultra_fast, url, start_idx + i): start_idx + i 
                for i in range(batch_size)
            }
            
            for future in as_completed(future_to_idx, timeout=40):
                window_idx = future_to_idx[future]
                try:
                    browser = future.result(timeout=10)
                    if browser:
                        successful_browsers.append(browser)
                except Exception as e:
                    print(f"❌ Window {window_idx} failed: {str(e)}")
        
        return len(successful_browsers)


    def predict(
        self,
        url: str = Input(
            description="Link to the website"
        ),
        num_windows: int = Input(
            description="Number of browser windows to open",
            default=1
        ),
        run_time_seconds: int = Input(
            description="How long to keep browsers open (0 = indefinite)",
            default=0
        ),
        maximum_mode: bool = Input(
            description="Enable maximum mode for absolute maximum browsers",
            default=True
        )
    ) -> str:
        self.running = True
        self.browsers = []
        
        try:
            print(f"🚀 GPU ULTRA-FAST MODE: Opening {num_windows} browsers at maximum speed...")
            print(f"⚡ Powerful GPU system - maximizing concurrent operations")
            print(f"💾 Memory limit: {self.max_memory_percent}%")
            
            # GPU-optimized batch sizes
            if num_windows <= 100:
                batch_size = 32
            elif num_windows <= 300:
                batch_size = 48
            elif num_windows <= 500:
                batch_size = 64
            elif num_windows <= 1000:
                batch_size = 80
            elif num_windows <= 2000:
                batch_size = 96
            else:
                batch_size = 128
            
            print(f"⚡ GPU MODE: Using batch size {batch_size} for maximum speed")
            
            total_opened = 0
            batch_number = 1
            
            # Open all browsers as fast as possible
            for batch_start in range(0, num_windows, batch_size):
                if not self.running:
                    break
                
                memory_usage = self.get_memory_usage()
                
                if memory_usage > self.max_memory_percent:
                    print(f"⚠️ Memory limit reached ({memory_usage}%) - stopping at {total_opened} browsers")
                    break
                
                current_batch_size = min(batch_size, num_windows - batch_start)
                print(f"⚡ GPU-batch {batch_number}: launching {current_batch_size} browsers ({batch_start + 1} to {batch_start + current_batch_size})")
                
                batch_success_count = self.gpu_batch_create(url, batch_start + 1, current_batch_size)
                total_opened += batch_success_count
                
                print(f"⚡ GPU-batch {batch_number} COMPLETE: {batch_success_count}/{current_batch_size} successful")
                print(f"📊 TOTAL BROWSERS: {total_opened}/{num_windows} | Memory: {self.get_memory_usage()}%")
                
                # Minimal pause for GPU processing
                if batch_start + batch_size < num_windows:
                    time.sleep(0.1)  # Minimal pause
                    gc.collect()
                
                batch_number += 1
            
            final_count = len(self.browsers)
            print(f"⚡🔥 ALL {final_count} BROWSERS OPENED at GPU speed for {url}")
            print(f"💾 Memory usage: {self.get_memory_usage()}%")
            
            # If run_time_seconds is 0, run forever - NEVER return success
            if run_time_seconds == 0:
                print(f"♾️ INFINITE MODE: {final_count} browsers running FOREVER - NEVER STOPPING")
                
                # Keep-alive system for infinite operation
                activity_counter = 0
                last_log = time.time()
                log_interval = 300  # Log every 5 minutes
                
                while True:  # INFINITE LOOP - NEVER STOP
                    # Enhanced keep-alive every 5 minutes
                    if activity_counter % 60 == 0:  # Every 5 minutes
                        active_browsers = 0
                        for browser in self.browsers:
                            try:
                                browser.execute_script("""
                                    window.infiniteMode = true;
                                    var videos = document.querySelectorAll('video');
                                    videos.forEach(function(video) {
                                        if (video.paused) {
                                            try { video.play(); } catch(e) {}
                                        }
                                    });
                                    window.scrollTo(0, Math.floor(Math.random() * 300));
                                """)
                                active_browsers += 1
                            except:
                                pass
                        print(f"♾️ {active_browsers} browsers active in INFINITE MODE...")
                    
                    # Log every 5 minutes
                    current_time = time.time()
                    if current_time - last_log >= log_interval:
                        elapsed = current_time - last_log
                        hours = int(elapsed // 3600)
                        minutes = int((elapsed % 3600) // 60)
                        memory_usage = self.get_memory_usage()
                        print(f"♾️ INFINITE MODE: {final_count} browsers running FOREVER | Memory: {memory_usage}% | URL: {url}")
                        last_log = current_time
                    
                    time.sleep(5)  # Check every 5 seconds
                    activity_counter += 1
            
            else:
                # Timed mode - run for specified time then keep running
                print(f"⏱️ TIMED MODE: {final_count} browsers running for {run_time_seconds} seconds")
                
                start_time = time.time()
                activity_counter = 0
                
                while time.time() - start_time < run_time_seconds:
                    # Keep browsers active
                    if activity_counter % 60 == 0:
                        active_browsers = 0
                        for browser in self.browsers:
                            try:
                                browser.execute_script("""
                                    window.timedMode = true;
                                    var videos = document.querySelectorAll('video');
                                    videos.forEach(function(video) {
                                        if (video.paused) {
                                            try { video.play(); } catch(e) {}
                                        }
                                    });
                                """)
                                active_browsers += 1
                            except:
                                pass
                    
                    elapsed = time.time() - start_time
                    remaining = run_time_seconds - elapsed
                    
                    if activity_counter % 60 == 0:  # Log every 5 minutes
                        memory_usage = self.get_memory_usage()
                        print(f"⏱️ {final_count} browsers active | {int(remaining)}s remaining | Memory: {memory_usage}%")
                    
                    time.sleep(5)
                    activity_counter += 1
                
                print(f"⏱️ TIMED MODE COMPLETE: {final_count} browsers finished {run_time_seconds} second run")
                return f"Timed mode complete: {final_count} browsers ran for {run_time_seconds} seconds"
                
        except Exception as e:
            print(f"⚠️ Error occurred: {str(e)}")
            # If infinite mode, continue despite errors
            if run_time_seconds == 0:
                print(f"♾️ INFINITE MODE continues despite error - {len(self.browsers)} browsers still running")
                while True:  # Continue infinite loop
                    time.sleep(60)
                    print(f"♾️ INFINITE MODE: {len(self.browsers)} browsers still running despite error")
            else:
                return f"Error occurred: {str(e)} - {len(self.browsers)} browsers remain active"


# Test runner function
def run_test(url="https://safe-dove-66.deno.dev/", num_windows=1000, run_time_seconds=0):
    """Run the browser automation test"""
    predictor = Predictor()
    predictor.setup()
    
    result = predictor.predict(
        url=url,
        num_windows=num_windows,
        run_time_seconds=run_time_seconds,
        maximum_mode=True
    )
    
    return result


if __name__ == "__main__":
    # Run with your specified parameters
    print("🚀 Starting browser automation test...")
    print("URL: https://safe-dove-66.deno.dev/")
    print("Windows: 1000")
    print("Mode: Infinite (run_time_seconds=0)")
    
    result = run_test(
        url="https://safe-dove-66.deno.dev/",
        num_windows=1000,
        run_time_seconds=0
    )
    
    print(f"Result: {result}")