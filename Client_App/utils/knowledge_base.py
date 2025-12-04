# utils/knowledge_base.py - Fixed version with proper error code matching
import json
import os
import logging
from config import Config

class KnowledgeBase:
    def __init__(self):
        self.config = Config()
        self.errors_db = self._load_knowledge_base()
    
    def _load_knowledge_base(self):
        """Load error knowledge base from JSON file"""
        try:
            if os.path.exists(self.config.KNOWLEDGE_BASE_PATH):
                with open(self.config.KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Create default knowledge base if it doesn't exist
                default_kb = self._create_default_knowledge_base()
                self._save_knowledge_base(default_kb)
                return default_kb
                
        except Exception as e:
            logging.error(f"Error loading knowledge base: {str(e)}")
            return {"errors": []}
    
    def _create_default_knowledge_base(self):
        """Create default knowledge base with common errors"""
        return {
            "errors": [
                {
                    "error_code": "0x0000001E",
                    "error_name": "KMODE_EXCEPTION_NOT_HANDLED",
                    "description": "A kernel-mode program generated an exception which the error handler didn't catch",
                    "category": "driver",
                    "confidence": "high",
                    "solutions": [
                        {
                            "step": 1,
                            "description": "Update all device drivers through Device Manager",
                            "details": "Press Win+X, select Device Manager, right-click devices with yellow warnings, select 'Update driver'"
                        },
                        {
                            "step": 2,
                            "description": "Run Windows Memory Diagnostic tool",
                            "details": "Press Win+R, type 'mdsched.exe', restart when prompted"
                        },
                        {
                            "step": 3,
                            "description": "Check for hardware issues",
                            "details": "Reseat RAM modules and check all cable connections"
                        }
                    ],
                    "additional_info": "Often caused by faulty drivers or hardware",
                    "gemini_context": "This error typically requires driver updates and memory testing. Be prepared to guide users through Device Manager navigation."
                },
                {
                    "error_code": "0x0000007E",
                    "error_name": "SYSTEM_THREAD_EXCEPTION_NOT_HANDLED",
                    "description": "A system thread generated an exception which the error handler didn't catch",
                    "category": "software",
                    "confidence": "high",
                    "solutions": [
                        {
                            "step": 1,
                            "description": "Boot in Safe Mode",
                            "details": "Hold Shift while clicking Restart, select Troubleshoot > Advanced Options > Startup Settings > Restart > F4"
                        },
                        {
                            "step": 2,
                            "description": "Uninstall recently installed software",
                            "details": "Go to Settings > Apps & features, sort by install date, uninstall recent programs"
                        },
                        {
                            "step": 3,
                            "description": "Update BIOS/UEFI firmware",
                            "details": "Visit manufacturer's website, download latest BIOS update for your motherboard model"
                        }
                    ],
                    "additional_info": "Usually caused by incompatible software or outdated system firmware",
                    "gemini_context": "Focus on recent software changes and system updates. Guide users through safe mode boot process."
                },
                {
                    "error_code": "0x00000050",
                    "error_name": "PAGE_FAULT_IN_NONPAGED_AREA",
                    "description": "Invalid system memory references, usually indicating hardware problems",
                    "category": "hardware",
                    "confidence": "high",
                    "solutions": [
                        {
                            "step": 1,
                            "description": "Test RAM with MemTest86",
                            "details": "Download MemTest86, create bootable USB, run full memory test overnight"
                        },
                        {
                            "step": 2,
                            "description": "Update system and device drivers",
                            "details": "Use Windows Update and visit manufacturer websites for latest drivers"
                        },
                        {
                            "step": 3,
                            "description": "Run full system scan for malware",
                            "details": "Use Windows Defender full scan or reputable antivirus software"
                        }
                    ],
                    "additional_info": "Often indicates failing RAM or storage devices",
                    "gemini_context": "This is typically a hardware issue. Help users understand memory testing procedures and hardware diagnostics."
                },
                {
                    "error_code": "0x0000000A",
                    "error_name": "IRQL_NOT_LESS_OR_EQUAL",
                    "description": "A kernel-mode process or driver attempted to access memory at too high an IRQL",
                    "category": "driver",
                    "confidence": "high",
                    "solutions": [
                        {
                            "step": 1,
                            "description": "Remove recently installed hardware",
                            "details": "Disconnect USB devices, remove new expansion cards, restore to previous hardware configuration"
                        },
                        {
                            "step": 2,
                            "description": "Update network and graphics drivers",
                            "details": "Visit AMD/NVIDIA/Intel websites for graphics drivers, router manufacturer for network drivers"
                        },
                        {
                            "step": 3,
                            "description": "Temporarily disable antivirus software",
                            "details": "Right-click antivirus system tray icon, select disable protection temporarily"
                        }
                    ],
                    "additional_info": "Usually caused by faulty drivers, especially network or graphics drivers",
                    "gemini_context": "Focus on driver conflicts and recent hardware changes. Help users identify problematic drivers."
                },
                {
                    "error_code": "0x000000EF",
                    "error_name": "CRITICAL_PROCESS_DIED",
                    "description": "A critical system process terminated unexpectedly",
                    "category": "system",
                    "confidence": "high",
                    "solutions": [
                        {
                            "step": 1,
                            "description": "Run System File Checker",
                            "details": "Open Command Prompt as administrator, run 'sfc /scannow', wait for completion"
                        },
                        {
                            "step": 2,
                            "description": "Reset Windows Update components",
                            "details": "Run 'net stop wuauserv', 'net stop cryptSvc', 'net stop bits', then restart these services"
                        },
                        {
                            "step": 3,
                            "description": "Perform System Restore",
                            "details": "Type 'rstrui.exe' in Run dialog, select restore point before the issue started"
                        }
                    ],
                    "additional_info": "Indicates corruption in critical Windows processes or files",
                    "gemini_context": "This is a serious system integrity issue. Guide users through system repair procedures carefully."
                }
            ]
        }
    
    def _save_knowledge_base(self, data):
        """Save knowledge base to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.config.KNOWLEDGE_BASE_PATH), exist_ok=True)
            with open(self.config.KNOWLEDGE_BASE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logging.info("Knowledge base saved successfully")
        except Exception as e:
            logging.error(f"Error saving knowledge base: {str(e)}")
    
    def search_solutions(self, error_code):
        """Search for solutions based on error code - FIXED VERSION"""
        try:
            if not error_code:
                logging.warning("No error code provided for solution search")
                return None
            
            # Clean and normalize error code
            clean_code = error_code.strip().upper()
            if not clean_code.startswith('0X'):
                if clean_code.startswith('0x'):
                    clean_code = clean_code.replace('0x', '0X')
                else:
                    clean_code = f"0X{clean_code}"
            
            logging.info(f"Searching for solutions for error code: {clean_code}")
            
            # Search through all errors in database
            for error in self.errors_db.get('errors', []):
                stored_code = error.get('error_code', '').strip().upper()
                logging.debug(f"Comparing {clean_code} with {stored_code}")
                
                if stored_code == clean_code:
                    logging.info(f"Found solution for error code: {clean_code}")
                    return {
                        'error_code': error['error_code'],
                        'error_name': error['error_name'],
                        'description': error['description'],
                        'category': error['category'],
                        'confidence': error['confidence'],
                        'solutions': error['solutions'],
                        'additional_info': error.get('additional_info', ''),
                        'gemini_context': error.get('gemini_context', '')
                    }
            
            logging.warning(f"No solution found for error code: {clean_code}")
            return None
            
        except Exception as e:
            logging.error(f"Error searching knowledge base: {str(e)}")
            return None
    
    def add_error(self, error_data):
        """Add new error to knowledge base"""
        try:
            self.errors_db['errors'].append(error_data)
            self._save_knowledge_base(self.errors_db)
            return True
        except Exception as e:
            logging.error(f"Error adding error to knowledge base: {str(e)}")
            return False
    
    def get_all_errors(self):
        """Get all errors from knowledge base"""
        return self.errors_db.get('errors', [])
    
    def debug_print_all_codes(self):
        """Debug method to print all error codes in database"""
        logging.info("All error codes in knowledge base:")
        for error in self.errors_db.get('errors', []):
            logging.info(f"  - {error.get('error_code', 'NO_CODE')}: {error.get('error_name', 'NO_NAME')}")

# Create the knowledge base JSON file if it doesn't exist
def create_knowledge_base_file():
    """Create the knowledge base JSON file"""
    kb_path = 'knowledge_base/errors.json'
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(kb_path), exist_ok=True)
    
    # Don't overwrite existing file
    if os.path.exists(kb_path):
        print(f"Knowledge base file already exists at {kb_path}")
        return
    
    # Create the knowledge base data
    kb_data = {
        "errors": [
            {
                "error_code": "0x0000001E",
                "error_name": "KMODE_EXCEPTION_NOT_HANDLED",
                "description": "A kernel-mode program generated an exception which the error handler didn't catch",
                "category": "driver",
                "confidence": "high",
                "solutions": [
                    {
                        "step": 1,
                        "description": "Update all device drivers through Device Manager",
                        "details": "Press Win+X, select Device Manager, right-click devices with yellow warnings, select 'Update driver'"
                    },
                    {
                        "step": 2,
                        "description": "Run Windows Memory Diagnostic tool",
                        "details": "Press Win+R, type 'mdsched.exe', restart when prompted"
                    },
                    {
                        "step": 3,
                        "description": "Check for hardware issues",
                        "details": "Reseat RAM modules and check all cable connections"
                    }
                ],
                "additional_info": "Often caused by faulty drivers or hardware",
                "gemini_context": "This error typically requires driver updates and memory testing."
            },
            {
                "error_code": "0x00000050",
                "error_name": "PAGE_FAULT_IN_NONPAGED_AREA",
                "description": "Invalid system memory references, usually indicating hardware problems",
                "category": "hardware",
                "confidence": "high",
                "solutions": [
                    {
                        "step": 1,
                        "description": "Test RAM with MemTest86",
                        "details": "Download MemTest86, create bootable USB, run full memory test overnight"
                    },
                    {
                        "step": 2,
                        "description": "Update system and device drivers",
                        "details": "Use Windows Update and visit manufacturer websites for latest drivers"
                    },
                    {
                        "step": 3,
                        "description": "Run full system scan for malware",
                        "details": "Use Windows Defender full scan or reputable antivirus software"
                    }
                ],
                "additional_info": "Often indicates failing RAM or storage devices",
                "gemini_context": "This is typically a hardware issue. Help users understand memory testing."
            }
        ]
    }
    
    # Write the file
    with open(kb_path, 'w', encoding='utf-8') as f:
        json.dump(kb_data, f, indent=2, ensure_ascii=False)
    
    print(f"Knowledge base file created at {kb_path}")

if __name__ == "__main__":
    create_knowledge_base_file()