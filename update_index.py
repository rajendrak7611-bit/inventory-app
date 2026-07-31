import re

with open('static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()
    
# We want to replace everything from <div class="layout-wrapper"> to just before <div class="table-container" id="productsSection">
pattern = r'(<div class="layout-wrapper">)(.*?)(<div class="table-container" id="productsSection">)'

replacement = '''<div class="menu-container">
        <nav class="main-menu-horizontal">
            <div class="main-tab" id="sidebarUsers" data-screen="users" style="display: none;">Users</div>
            <div class="main-tab" id="sidebarMaster" data-group="master">Master</div>
            <div class="main-tab" id="sidebarInventory" data-group="inventory">Inventory</div>
            <div class="main-tab" id="sidebarProduction" data-group="production">Production</div>
            <div class="main-tab active" id="sidebarProducts" data-screen="products">Tool Crib</div>
            <div class="main-tab" id="sidebarInspection" data-screen="inspection">Inspection</div>
            <div class="main-tab" id="sidebarReports" data-group="reports">Reports</div>
            <div class="main-tab" id="sidebarMaintenance" data-screen="maintenance">Maintenance</div>
            <div class="main-tab" id="sidebarHR" data-screen="hr">HR</div>
        </nav>
        <nav class="sub-menu-horizontal">
            <div class="sub-group" id="submenuMaster" style="display: none;">
                <button class="sub-tab" id="sidebarPartMaster" data-screen="partmaster">Part Master</button>
                <button class="sub-tab" id="sidebarMachines" data-screen="machines">Machines</button>
                <button class="sub-tab" id="sidebarOperators" data-screen="operators">Operators</button>
            </div>
            <div class="sub-group" id="submenuInventory" style="display: none;">
                <button class="sub-tab" id="sidebarRmReceipt" data-screen="rawmaterial">Receipt</button>
                <button class="sub-tab" id="sidebarRmDespatch" data-screen="rawmaterial">Despatch</button>
                <button class="sub-tab" id="sidebarRmMaster" data-screen="rawmaterial">RM Status</button>
            </div>
            <div class="sub-group" id="submenuProduction" style="display: none;">
                <button class="sub-tab" id="sidebarScheduleCreate" data-screen="schedule">Schedule Create</button>
                <button class="sub-tab" id="sidebarScheduleRun" data-screen="schedule">Schedule Run</button>
                <button class="sub-tab" id="sidebarStatus" data-screen="status">Status</button>
                <button class="sub-tab" id="sidebarProdLog" data-screen="prodlog">Prod Log</button>
                <button class="sub-tab" id="sidebarDebur" data-screen="debur">Debur</button>
            </div>
            <div class="sub-group" id="submenuReports" style="display: none;">
                <button class="sub-tab" id="sidebarRmRequirement" data-screen="reports">RM Requirement</button>
            </div>
        </nav>
    </div>
    <main class="content">
        ''' + r'\3'

new_html = re.sub(pattern, replacement, html, flags=re.DOTALL)
with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(new_html)
print('Updated index.html')
