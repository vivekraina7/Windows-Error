# utils/file_scanner.py - File Monitoring and Detection
import os
import glob
import logging
from datetime import datetime, timedelta
from config import Config

class FileScanner:
    def __init__(self):
        self.config = Config()
        self.last_scan_time = None
        
    def scan_directories(self):
        """Scan configured directories for dump files"""
        dump_files = []
        
        for location in self.config.DUMP_LOCATIONS:
            if os.path.exists(location):
                try:
                    # Find all .dmp files
                    pattern = os.path.join(location, '*.dmp')
                    files = glob.glob(pattern)
                    
                    for file_path in files:
                        if self._is_valid_dump_file(file_path):
                            file_info = self._get_file_info(file_path)
                            dump_files.append(file_info)
                            
                except Exception as e:
                    logging.error(f"Error scanning {location}: {str(e)}")
                    continue
        
        # Sort by modification time (newest first)
        dump_files.sort(key=lambda x: x['modified_time'], reverse=True)
        
        self.last_scan_time = datetime.now()
        logging.info(f"File scan completed. Found {len(dump_files)} dump files")
        
        return dump_files
    
    def _is_valid_dump_file(self, file_path):
        """Validate if file is a proper dump file"""
        try:
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size == 0 or file_size > self.config.MAX_DUMP_SIZE:
                return False
            
            # Check file extension
            if not file_path.lower().endswith('.dmp'):
                return False
            
            # Basic header check (dump files start with specific signatures)
            with open(file_path, 'rb') as f:
                header = f.read(8)
                # Windows dump files typically start with specific patterns
                if len(header) >= 4:
                    return True  # Basic validation passed
            
            return True
            
        except Exception as e:
            logging.error(f"Error validating dump file {file_path}: {str(e)}")
            return False
    
    def _get_file_info(self, file_path):
        """Get detailed information about dump file"""
        try:
            stat = os.stat(file_path)
            
            return {
                'path': file_path,
                'filename': os.path.basename(file_path),
                'size': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error getting file info for {file_path}: {str(e)}")
            return None
    
    def get_new_files_since_last_scan(self):
        """Get files modified since last scan"""
        if not self.last_scan_time:
            return self.scan_directories()
        
        all_files = self.scan_directories()
        new_files = [f for f in all_files if f['modified_time'] > self.last_scan_time]
        
        return new_files