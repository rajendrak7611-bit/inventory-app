
import sys

def replace_all(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    reps = {
        'tabUsers': 'sidebarUsers',
        'menuRmReceipt': 'sidebarRmReceipt',
        'menuRmDespatch': 'sidebarRmDespatch',
        'menuRmMaster': 'sidebarRmMaster',
        'tabProducts': 'sidebarProducts',
        'tabPartMaster': 'sidebarPartMaster',
        'tabMachines': 'sidebarMachines',
        'tabOperators': 'sidebarOperators',
        'menuScheduleCreate': 'sidebarScheduleCreate',
        'menuScheduleRun': 'sidebarScheduleRun',
        'tabStatus': 'sidebarStatus',
        'tabProdLog': 'sidebarProdLog',
        'tabDebur': 'sidebarDebur',
        'tabInspection': 'sidebarInspection',
        'menuRmRequirement': 'sidebarRmRequirement',
        '.tab-btn': '.sidebar-item'
    }

    for k, v in reps.items():
        content = content.replace(k, v)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

replace_all('./static/app.js')

