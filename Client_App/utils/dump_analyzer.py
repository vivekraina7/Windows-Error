# utils/dump_analyzer.py - Fixed with missing datetime import and category detection
import os
import subprocess
import re
import logging
from datetime import datetime
from config import Config

class DumpAnalyzer:
    def __init__(self):
        self.config = Config()
        
    def analyze_dump(self, file_info):
        """Analyze dump file and extract error information"""
        try:
            file_path = file_info['path']
            logging.info(f"Analyzing dump file: {file_path}")
            
            # Try different analysis methods
            analysis = self._analyze_with_windbg(file_path)
            
            if not analysis:
                analysis = self._analyze_basic_pattern(file_path)
            
            if analysis:
                # Convert datetime objects in file_info to ISO format strings
                if 'file_info' in analysis:
                    if 'modified_time' in analysis['file_info'] and isinstance(analysis['file_info']['modified_time'], datetime):
                        analysis['file_info']['modified_time'] = analysis['file_info']['modified_time'].isoformat()
                    if 'created_time' in analysis['file_info'] and isinstance(analysis['file_info']['created_time'], datetime):
                        analysis['file_info']['created_time'] = analysis['file_info']['created_time'].isoformat()

                analysis.update({
                    'file_info': file_info,
                    'analysis_time': datetime.now().isoformat(),
                    'analyzer_method': analysis.get('method', 'unknown')
                })
            
            return analysis
            
        except Exception as e:
            logging.error(f"Error analyzing dump file {file_info['path']}: {str(e)}")
            return None
    
    def _analyze_with_windbg(self, file_path):
        """Analyze dump using WinDbg command line"""
        try:
            if not os.path.exists(self.config.WINDBG_PATH):
                logging.warning("WinDbg not found, using alternative analysis")
                return None
            
            cmd = [
                self.config.WINDBG_PATH,
                '-z', file_path,
                '-c', '!analyze -v; q',
                '-logo', 'nul'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return self._parse_windbg_output(result.stdout)
            else:
                logging.error(f"WinDbg analysis failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logging.error("WinDbg analysis timed out")
            return None
        except Exception as e:
            logging.error(f"Error running WinDbg: {str(e)}")
            return None
    
    def _parse_windbg_output(self, output):
        """Parse WinDbg output to extract error information"""
        try:
            analysis = {'method': 'windbg'}
            
            # Extract bug check code
            bug_check_match = re.search(r'BUGCHECK_CODE:\s+([0-9a-fA-F]+)', output)
            if bug_check_match:
                analysis['error_code'] = f"0X{bug_check_match.group(1).upper().zfill(8)}"
            
            # Extract bug check string
            bug_check_str_match = re.search(r'BUGCHECK_STR:\s+(.+)', output)
            if bug_check_str_match:
                analysis['error_name'] = bug_check_str_match.group(1).strip()
            
            # Extract faulting module
            module_match = re.search(r'MODULE_NAME:\s+(.+)', output)
            if module_match:
                analysis['faulting_module'] = module_match.group(1).strip()
            
            # Extract process name
            process_match = re.search(r'PROCESS_NAME:\s+(.+)', output)
            if process_match:
                analysis['process_name'] = process_match.group(1).strip()
            
            return analysis if analysis.get('error_code') else None
            
        except Exception as e:
            logging.error(f"Error parsing WinDbg output: {str(e)}")
            return None
    
    def _analyze_basic_pattern(self, file_path):
        """Basic pattern matching analysis for common dump signatures"""
        try:
            analysis = {'method': 'pattern_matching'}
            
            # Read first few KB of dump file
            with open(file_path, 'rb') as f:
                header_data = f.read(8192)  # Read first 8KB
            
            # Convert to hex string for pattern matching
            hex_data = header_data.hex().upper()
            
            # Common bug check codes mapping
            common_codes = {
                '0000001E': {
                    'name': 'KMODE_EXCEPTION_NOT_HANDLED',
                    'category': 'driver'
                },
                '0000007E': {
                    'name': 'SYSTEM_THREAD_EXCEPTION_NOT_HANDLED',
                    'category': 'software'
                },
                '00000050': {
                    'name': 'PAGE_FAULT_IN_NONPAGED_AREA',
                    'category': 'hardware'
                },
                '0000000A': {
                    'name': 'IRQL_NOT_LESS_OR_EQUAL',
                    'category': 'driver'
                },
                '000000EF': {
                    'name': 'CRITICAL_PROCESS_DIED',
                    'category': 'system'
                }
            }
            
            # Look for patterns in hex data
            for code, info in common_codes.items():
                if code in hex_data:
                    analysis['error_code'] = f"0X{code}"
                    analysis['error_name'] = info['name']
                    analysis['category'] = info['category']
                    analysis['confidence'] = 'medium'
                    break
            
            # If no specific pattern found, create generic analysis
            if 'error_code' not in analysis:
                analysis['error_code'] = '0X00000000'
                analysis['error_name'] = 'UNKNOWN_ERROR'
                analysis['category'] = 'unknown'
                analysis['confidence'] = 'low'
            
            return analysis
            
        except Exception as e:
            logging.error(f"Error in basic pattern analysis: {str(e)}")
            return None
