document.addEventListener('DOMContentLoaded', () => {
    // --- LOGIN LOGIC ---
    const loginOverlay = document.getElementById('loginOverlay');
    const loginForm = document.getElementById('loginForm');
    const loginError = document.getElementById('loginError');
    const appContainer = document.querySelector('.app-container');

    const currentUser = localStorage.getItem('grs_user');
    let userObj = null;
    try {
        if (currentUser) userObj = JSON.parse(currentUser);
    } catch(e) {}

    if (!userObj) {
        appContainer.style.display = 'none';
    } else {
        loginOverlay.style.display = 'none';
        
        // Access Control Logic
        const allTabs = document.querySelectorAll('.sidebar-menu [data-screen]');
        let firstAvailableTab = null;
        let accessibleScreens = [];
        try {
            accessibleScreens = JSON.parse(userObj.accessible_screens || '[]');
        } catch(e) {}
        
        allTabs.forEach(tab => {
            const screen = tab.getAttribute('data-screen');
            if (userObj.role === 'admin' || accessibleScreens.includes(screen)) {
                tab.style.display = (screen === 'schedule') ? 'inline-block' : 'inline-block';
                if (!firstAvailableTab) firstAvailableTab = tab;
            } else {
                tab.style.display = 'none';
            }
        });
        
        // Hide parent submenu if all children are hidden
        document.querySelectorAll('.main-tab.has-submenu').forEach(parent => {
            const submenu = parent.nextElementSibling;
            if (submenu && submenu.classList.contains('sidebar-submenu')) {
                const visibleChildren = Array.from(submenu.querySelectorAll('.main-tab')).some(child => child.style.display !== 'none');
                parent.style.display = visibleChildren ? 'flex' : 'none';
            }
        });
        
        // Special case for Users tab
        const sidebarUsers = document.getElementById('sidebarUsers');
        if (userObj.role === 'admin') {
            sidebarUsers.style.display = 'inline-block';
        } else {
            sidebarUsers.style.display = 'none';
        }

        // Add logout button to header actions div
        const actionDiv = document.getElementById('headerActions');
        const logoutBtn = document.createElement('button');
        logoutBtn.className = 'btn btn-secondary';
        logoutBtn.textContent = `Logout (${userObj.username})`;
        logoutBtn.onclick = () => {
            localStorage.removeItem('grs_user');
            window.location.reload();
        };
        actionDiv.appendChild(logoutBtn);

        // Auto-click the first available tab if they don't have access to the default (products)
        if (userObj.role !== 'admin' && firstAvailableTab && !accessibleScreens.includes('products')) {
            setTimeout(() => {
                firstAvailableTab.click();
            }, 100);
        }
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        loginError.style.display = 'none';
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        
        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            if (res.ok) {
                const data = await res.json();
                localStorage.setItem('grs_user', JSON.stringify(data));
                window.location.reload();
            } else {
                loginError.style.display = 'block';
            }
        } catch (err) {
            console.error(err);
            loginError.style.display = 'block';
        }
    });

    // Shared
    const addBtn = document.getElementById('addBtn');
    const importBtn = document.getElementById('importBtn');
    const importFile = document.getElementById('importFile');
    let currentTab = 'products';
    let availableMachines = [];

    // Tabs
    const tabRawMaterial = document.getElementById('tabRawMaterial');
    const sidebarRmMaster = document.getElementById('sidebarRmMaster');
    const sidebarRmReceipt = document.getElementById('sidebarRmReceipt');
    const sidebarRmDespatch = document.getElementById('sidebarRmDespatch');
    
    const sidebarProducts = document.getElementById('sidebarProducts');
    const sidebarPartMaster = document.getElementById('sidebarPartMaster');
    const sidebarMachines = document.getElementById('sidebarMachines');
    const sidebarOperators = document.getElementById('sidebarOperators');
    const tabSchedule = document.getElementById('tabSchedule');
    const sidebarScheduleCreate = document.getElementById('sidebarScheduleCreate');
    const sidebarScheduleRun = document.getElementById('sidebarScheduleRun');
    const sidebarStatus = document.getElementById('sidebarStatus');
    const sidebarProdLog = document.getElementById('sidebarProdLog');
    const sidebarDebur = document.getElementById('sidebarDebur');
    const sidebarInspection = document.getElementById('sidebarInspection');
    
    const rawMaterialsSection = document.getElementById('rawMaterialsSection');
    const rmReceiptSection = document.getElementById('rmReceiptSection');
    const rmDespatchSection = document.getElementById('rmDespatchSection');
    const productsSection = document.getElementById('productsSection');
    const partMasterSection = document.getElementById('partMasterSection');
    const machinesSection = document.getElementById('machinesSection');
    const operatorsSection = document.getElementById('operatorsSection');
    const scheduleCreateSection = document.getElementById('scheduleCreateSection');
    const scheduleRunSection = document.getElementById('scheduleRunSection');
    const scheduleStatusSection = document.getElementById('scheduleStatusSection');
    const prodLogSection = document.getElementById('prodLogSection');
    const deburSection = document.getElementById('deburSection');
    const inspectionSection = document.getElementById('inspectionSection');

    // Products Elements
    const productsBody = document.getElementById('productsBody');
    const productModal = document.getElementById('productModal');
    const productForm = document.getElementById('productForm');
    const closeProductBtn = document.getElementById('closeModalBtn');
    const cancelProductBtn = document.getElementById('cancelBtn');
    const productModalTitle = document.getElementById('modalTitle');

    // Part Master Elements
    const partMasterBody = document.getElementById('partMasterBody');
    const partModal = document.getElementById('partModal');
    const partForm = document.getElementById('partForm');
    const closePartBtn = document.getElementById('closePartModalBtn');
    const cancelPartBtn = document.getElementById('cancelPartBtn');
    const partModalTitle = document.getElementById('partModalTitle');

    // Operations Elements
    const operationsModal = document.getElementById('operationsModal');
    const closeOperationsModalBtn = document.getElementById('closeOperationsModalBtn');
    const cancelOperationsBtn = document.getElementById('cancelOperationsBtn');
    const saveOperationsBtn = document.getElementById('saveOperationsBtn');
    const operationsBody = document.getElementById('operationsBody');
    const operationsPartId = document.getElementById('operationsPartId');

    // Machine Elements
    const machinesBody = document.getElementById('machinesBody');
    const machineModal = document.getElementById('machineModal');
    const machineForm = document.getElementById('machineForm');
    const closeMachineBtn = document.getElementById('closeMachineModalBtn');
    const cancelMachineBtn = document.getElementById('cancelMachineBtn');
    const machineModalTitle = document.getElementById('machineModalTitle');

    // Operator Elements
    const operatorsBody = document.getElementById('operatorsBody');
    const operatorModal = document.getElementById('operatorModal');
    const operatorForm = document.getElementById('operatorForm');
    const closeOperatorBtn = document.getElementById('closeOperatorModalBtn');
    const cancelOperatorBtn = document.getElementById('cancelOperatorBtn');
    const operatorModalTitle = document.getElementById('operatorModalTitle');


    function hideAllSections() {
        const sections = [
            'usersSection', 'reportsSection', 'rmRequirementSection', 
            'rawMaterialsSection', 'rmReceiptSection', 'rmDespatchSection',
            'productsSection', 'partMasterSection', 'machinesSection',
            'operatorsSection', 'scheduleCreateSection', 'scheduleRunSection',
            'scheduleStatusSection', 'prodLogSection', 'deburSection',
            'inspectionSection', 'maintenanceSection', 'hrSection'
        ];
        sections.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        
        document.querySelectorAll('.main-tab').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.sub-tab').forEach(btn => btn.classList.remove('active'));
        importBtn.style.display = 'none';
        addBtn.style.display = 'inline-flex';
    }

    function hideAllSubmenus() {
        document.querySelectorAll('.sub-group').forEach(grp => {
            grp.style.display = 'none';
        });
    }

    // Main Menu Click Handler
    document.querySelectorAll('.main-tab').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            document.querySelectorAll('.main-tab').forEach(btn => btn.classList.remove('active'));
            item.classList.add('active');
            
            const group = item.getAttribute('data-group');
            const screen = item.getAttribute('data-screen');
            
            if (group) {
                hideAllSubmenus();
                const submenu = document.getElementById('submenu' + group.charAt(0).toUpperCase() + group.slice(1));
                if (submenu) {
                    submenu.style.display = 'flex';
                    // Auto-click first tab in submenu
                    const firstTab = submenu.querySelector('.sub-tab');
                    if (firstTab) firstTab.click();
                }
            } else if (screen) {
                hideAllSubmenus();
                hideAllSections();
                
                // Specific direct links
                if (screen === 'products') {
                    currentTab = 'products';
                    productsSection.style.display = 'block';
                    addBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Tool';
                    addBtn.style.display = 'inline-flex';
                    fetchProducts();
                } else if (screen === 'users') {
                    currentTab = 'users';
                    const usersSection = document.getElementById('usersSection');
                    if (usersSection) usersSection.style.display = 'block';
                    addBtn.style.display = 'none';
                    fetchUsers();
                } else if (screen === 'inspection') {
                    currentTab = 'inspection';
                    inspectionSection.style.display = 'block';
                    addBtn.style.display = 'none';
                    initInspection();
                } else if (screen === 'maintenance') {
                    currentTab = 'maintenance';
                    const mSec = document.getElementById('maintenanceSection');
                    if (mSec) mSec.style.display = 'block';
                    addBtn.style.display = 'none';
                } else if (screen === 'hr') {
                    currentTab = 'hr';
                    const hrSec = document.getElementById('hrSection');
                    if (hrSec) hrSec.style.display = 'block';
                    addBtn.style.display = 'none';
                }
            }
        });
    });

    // Sub-tab Click Handlers
    const subTabs = {
        'sidebarPartMaster': { tab: 'partmaster', action: () => { 
            partMasterSection.style.display = 'block'; 
            importBtn.style.display = 'inline-block';
            addBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Part';
            fetchPartMasters(); 
        }},
        'sidebarMachines': { tab: 'machines', action: () => { 
            machinesSection.style.display = 'block'; 
            importBtn.style.display = 'inline-block';
            addBtn.style.display = 'inline-flex';
            addBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Machine';
            fetchMachines(); 
        }},
        'sidebarOperators': { tab: 'operators', action: () => { 
            operatorsSection.style.display = 'block'; 
            importBtn.style.display = 'inline-block';
            addBtn.style.display = 'inline-flex';
            addBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Operator';
            fetchOperators(); 
        }},
        'sidebarRmReceipt': { tab: 'rm_receipt', action: () => { 
            if (rmReceiptSection) rmReceiptSection.style.display = 'block';
            addBtn.innerHTML = '<i class="fas fa-plus"></i> Add Receipt';
            importBtn.style.display = 'inline-flex';
            fetchRmLogs('receipt');
        }},
        'sidebarRmDespatch': { tab: 'rm_despatch', action: () => { 
            if (rmDespatchSection) rmDespatchSection.style.display = 'block';
            addBtn.innerHTML = '<i class="fas fa-plus"></i> Add Despatch';
            importBtn.style.display = 'inline-flex';
            fetchRmLogs('despatch');
        }},
        'sidebarRmMaster': { tab: 'rawmaterial', action: () => { 
            if (rawMaterialsSection) rawMaterialsSection.style.display = 'block';
            addBtn.innerHTML = '<i class="fas fa-plus"></i> Add Raw Material';
            importBtn.style.display = 'inline-flex';
            fetchRawMaterials();
        }},
        'sidebarRmRequirement': { tab: 'rm_requirement', action: () => { 
            const rmReqSec = document.getElementById('rmRequirementSection');
            if (rmReqSec) rmReqSec.style.display = 'block';
            addBtn.style.display = 'none';
            fetchRmRequirement();
        }},
        'sidebarScheduleCreate': { tab: 'schedule_create', action: () => { 
            scheduleCreateSection.style.display = 'block'; 
            addBtn.style.display = 'none'; 
            fetchScheduleOptions(); 
        }},
        'sidebarScheduleRun': { tab: 'schedule_run', action: () => { 
            scheduleRunSection.style.display = 'block'; 
            addBtn.style.display = 'none'; 
            fetchScheduleRuns(); 
        }},
        'sidebarStatus': { tab: 'status', action: () => { 
            scheduleStatusSection.style.display = 'block'; 
            addBtn.style.display = 'none'; 
            initScheduleStatus(); 
        }},
        'sidebarProdLog': { tab: 'prodlog', action: () => { 
            prodLogSection.style.display = 'block'; 
            addBtn.style.display = 'none'; 
            initProdLog(); 
        }},
        'sidebarDebur': { tab: 'debur', action: () => { 
            deburSection.style.display = 'block'; 
            addBtn.style.display = 'none'; 
            initDebur(); 
        }}
    };

    document.querySelectorAll('.sub-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            hideAllSections();
            document.querySelectorAll('.sub-tab').forEach(btn => btn.classList.remove('active'));
            tab.classList.add('active');
            
            const config = subTabs[tab.id];
            if (config) {
                currentTab = config.tab;
                config.action();
            }
        });
    });

    addBtn.addEventListener('click', () => {
        if (currentTab === 'products') openProductModal(false);
        else if (currentTab === 'partmaster') openPartModal(false);
        else if (currentTab === 'machines') openMachineModal(false);
        else if (currentTab === 'operators') openOperatorModal(false);
        else if (currentTab === 'rawmaterial') {
            document.getElementById('rmModalTitle').innerText = 'Add Raw Material';
            document.getElementById('rawMaterialForm').reset();
            document.getElementById('rmId').value = '';
            document.getElementById('rawMaterialModal').classList.add('show');
        }
        else if (currentTab === 'rm_receipt' || currentTab === 'rm_despatch') {
            const isReceipt = currentTab === 'rm_receipt';
            document.getElementById('rmLogModalTitle').innerText = isReceipt ? 'Add Receipt' : 'Add Despatch';
            document.getElementById('rmLogForm').reset();
            document.getElementById('rmLogType').value = isReceipt ? 'receipt' : 'despatch';
            
            // Populate datalist with forge PNs
            const list = document.getElementById('forgePnList');
            list.innerHTML = '';
            allRawMaterials.forEach(rm => {
                const opt = document.createElement('option');
                opt.value = rm.forge_pn;
                list.appendChild(opt);
            });
            
            // Default date to today
            document.getElementById('rmLogDate').value = new Date().toISOString().split('T')[0];
            document.getElementById('rmLogModal').classList.add('show');
        }
    });

    // Excel Import Logic
    importBtn.addEventListener('click', () => {
        importFile.click();
    });

    importFile.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async (evt) => {
            try {
                const data = evt.target.result;
                const workbook = XLSX.read(data, { type: 'binary' });
                const sheetName = workbook.SheetNames[0];
                const sheet = workbook.Sheets[sheetName];
                const json = XLSX.utils.sheet_to_json(sheet);

                let endpoint = '';
                let bodyData = '';

                if (currentTab === 'partmaster') {
                    const partsMap = {};
                    json.forEach(row => {
                        const partno = String(row['part no'] || row['Part no'] || row['Part No'] || row['partno'] || '').trim();
                        if (!partno) return;

                        if (!partsMap[partno]) {
                            partsMap[partno] = {
                                family: String(row['Family'] || row['family'] || '').trim(),
                                forge_pn: String(row['Forge pn'] || row['forge_pn'] || row['Forge PN'] || '').trim(),
                                partno: partno,
                                department: String(row['Dept'] || row['dept'] || row['Department'] || row['department'] || '').trim(),
                                va: String(row['VA'] || row['va'] || row['Va'] || '').trim(),
                                operations: []
                            };
                        }

                        if (row['Opn no'] !== undefined || row['Description']) {
                            partsMap[partno].operations.push({
                                opn_no: String(row['Opn no'] || row['opn_no'] || row['Opn No'] || '').trim(),
                                description: String(row['Description'] || row['description'] || '').trim(),
                                machine: String(row['Machine'] || row['machine'] || '').trim(),
                                cycle_time: parseFloat(row['cycle time'] || row['Cycle time'] || row['Cycle Time'] || row['cycle_time']) || 0
                            });
                        }
                    });
                    endpoint = '/api/partmaster/bulk_import';
                    bodyData = JSON.stringify({ parts: Object.values(partsMap) });
                } else if (currentTab === 'machines') {
                    const machines = [];
                    json.forEach(row => {
                        const name = String(row['Machine Name'] || row['machine name'] || row['Machine'] || '').trim();
                        if (!name) return;
                        machines.push({
                            name: name,
                            department: String(row['Dept'] || row['dept'] || row['Department'] || row['department'] || '').trim()
                        });
                    });
                    endpoint = '/api/machines/bulk_import';
                    bodyData = JSON.stringify({ machines: machines });
                } else if (currentTab === 'operators') {
                    const operators = [];
                    json.forEach(row => {
                        const name = String(row['Name'] || row['name'] || row['Operator Name'] || '').trim();
                        if (!name) return;
                        operators.push({
                            name: name,
                            department: String(row['Dept'] || row['dept'] || row['Department'] || row['department'] || '').trim()
                        });
                    });
                    endpoint = '/api/operators/bulk_import';
                    bodyData = JSON.stringify({ operators: operators });
                } else if (currentTab === 'rawmaterial') {
                    const rawmaterials = [];
                    json.forEach(row => {
                        const forge_pn = String(row['Forge PN'] || row['FORGE PN'] || row['Forge Pn'] || row['forge_pn'] || row['Forge pn'] || '').trim();
                        if (!forge_pn) return;
                        
                        // Treat 'Quantity' or 'Stock' or 'Receipt' column as the quantity
                        const quantity = parseInt(row['Quantity'] || row['QUANTITY'] || row['Qty'] || row['qty'] || row['Stock'] || row['Receipt'] || 0) || 0;
                        const receipt = quantity;
                        const despatch = 0;
                        const stock = quantity;
                        
                        rawmaterials.push({ forge_pn, receipt, despatch, stock });
                    });
                    
                    if (rawmaterials.length === 0) {
                        alert("No valid raw material data found. Please check column headers (e.g., 'Forge PN', 'Quantity').");
                        return;
                    }
                    
                    endpoint = '/api/rawmaterials/bulk';
                    bodyData = JSON.stringify({ rawmaterials: rawmaterials });
                } else if (currentTab === 'rm_receipt' || currentTab === 'rm_despatch') {
                    const logs = [];
                    const type = currentTab === 'rm_receipt' ? 'receipt' : 'despatch';
                    json.forEach(row => {
                        const forge_pn = String(row['Forge PN'] || row['FORGE PN'] || row['Forge Pn'] || row['forge_pn'] || row['Forge pn'] || '').trim();
                        if (!forge_pn) return;
                        
                        const qty = parseInt(row['Quantity'] || row['QUANTITY'] || row['Qty'] || row['qty'] || 0) || 0;
                        if (qty <= 0) return;
                        
                        let date = row['Date'] || row['DATE'] || row['date'];
                        if (!date) {
                            date = new Date().toISOString().split('T')[0];
                        } else {
                            // Excel serial dates mapping if it's a number
                            if (typeof date === 'number') {
                                const d = new Date((date - 25569) * 86400 * 1000);
                                date = d.toISOString().split('T')[0];
                            }
                        }
                        
                        logs.push({ type, date, forge_pn, qty });
                    });
                    
                    if (logs.length === 0) {
                        alert("No valid log data found. Please check column headers (e.g., 'Forge PN', 'Quantity').");
                        return;
                    }
                    
                    endpoint = '/api/rawmateriallogs/bulk';
                    bodyData = JSON.stringify({ logs: logs });
                }

                if (!endpoint) {
                    alert('Import is not supported on this tab.');
                    importBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 4px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg> Import Excel`;
                    importBtn.disabled = false;
                    importFile.value = '';
                    return;
                }
                
                // Show loading indicator on button
                importBtn.innerHTML = 'Importing...';
                importBtn.disabled = true;

                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: bodyData
                });

                if (response.ok) {
                    alert('Import successful!');
                    if (currentTab === 'partmaster') fetchPartMasters();
                    else if (currentTab === 'machines') fetchMachines();
                    else if (currentTab === 'operators') fetchOperators();
                    else if (currentTab === 'rawmaterial') fetchRawMaterials();
                    else if (currentTab === 'rm_receipt') fetchRmLogs('receipt');
                    else if (currentTab === 'rm_despatch') fetchRmLogs('despatch');
                } else {
                    alert('Import failed. Please check the console.');
                }
            } catch (err) {
                console.error('Error importing file:', err);
                alert('Error parsing the file. Make sure it is a valid Excel format.');
            } finally {
                importBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 4px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg> Import Excel`;
                importBtn.disabled = false;
                importFile.value = ''; // Reset file input
            }
        };
        reader.readAsBinaryString(file);
    });

    // --- PRODUCTS LOGIC ---
    async function fetchProducts() {
        try {
            const response = await fetch('/api/products');
            const products = await response.json();
            productsBody.innerHTML = '';
            if (products.length === 0) {
                productsBody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted)">No tools found. Add one!</td></tr>';
                return;
            }
            products.forEach(p => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${p.id}</td><td>${p.family}</td><td>${p.spec}</td><td>${p.make}</td>
                    <td>${p.stock}</td><td>Rs ${p.price.toFixed(2)}</td>
                    <td class="actions">
                        <button class="btn btn-edit" onclick="editProduct(${p.id})">Edit</button>
                        <button class="btn btn-danger" onclick="deleteProduct(${p.id})">Delete</button>
                    </td>`;
                productsBody.appendChild(tr);
            });
        } catch (e) { console.error(e); }
    }

    function openProductModal(isEdit) {
        productModal.classList.add('show');
        productModalTitle.textContent = isEdit ? 'Edit Tool' : 'Add Tool';
    }
    function closeProductModal() { productModal.classList.remove('show'); productForm.reset(); document.getElementById('productId').value = ''; }
    closeProductBtn.addEventListener('click', closeProductModal); cancelProductBtn.addEventListener('click', closeProductModal);

    productForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('productId').value;
        const data = {
            family: document.getElementById('family').value, spec: document.getElementById('spec').value,
            make: document.getElementById('make').value, stock: parseInt(document.getElementById('stock').value),
            price: parseFloat(document.getElementById('price').value)
        };
        const url = id ? `/api/products/${id}` : '/api/products';
        await fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        closeProductModal(); fetchProducts();
    });

    window.deleteProduct = async (id) => {
        if (confirm('Delete this tool?')) {
            await fetch(`/api/products/${id}`, { method: 'DELETE' });
            fetchProducts();
        }
    };
    window.editProduct = async (id) => {
        const res = await fetch('/api/products'); const data = await res.json();
        const p = data.find(x => x.id === id);
        if (p) {
            document.getElementById('productId').value = p.id; document.getElementById('family').value = p.family;
            document.getElementById('spec').value = p.spec; document.getElementById('make').value = p.make;
            document.getElementById('stock').value = p.stock; document.getElementById('price').value = p.price;
            openProductModal(true);
        }
    };

    // --- PART MASTER LOGIC ---
    async function fetchPartMasters() {
        try {
            const response = await fetch('/api/partmaster');
            const parts = await response.json();
            partMasterBody.innerHTML = '';
            if (parts.length === 0) {
                partMasterBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">No part masters found.</td></tr>';
                return;
            }
            parts.forEach(p => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${p.id}</td><td>${p.department || ''}</td><td>${p.family}</td><td>${p.forge_pn}</td><td>${p.partno}</td><td>${p.va || ''}</td>
                    <td class="actions">
                        <button class="btn btn-outline" style="margin-right: 5px;" onclick="openOperations(${p.id})">Operations</button>
                        <button class="btn btn-edit" onclick="editPartMaster(${p.id})">Edit</button>
                        <button class="btn btn-danger" onclick="deletePartMaster(${p.id})">Delete</button>
                    </td>`;
                partMasterBody.appendChild(tr);
            });
        } catch (e) { console.error(e); }
    }

    function openPartModal(isEdit) {
        partModal.classList.add('show');
        partModalTitle.textContent = isEdit ? 'Edit Part' : 'Add Part';
    }
    function closePartModal() { partModal.classList.remove('show'); partForm.reset(); document.getElementById('partId').value = ''; }
    closePartBtn.addEventListener('click', closePartModal); cancelPartBtn.addEventListener('click', closePartModal);

    partForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('partId').value;
        const data = {
            family: document.getElementById('partFamily').value, forge_pn: document.getElementById('forgePn').value,
            partno: document.getElementById('partno').value, department: document.getElementById('partDept').value,
            va: document.getElementById('partVa').value
        };
        const url = id ? `/api/partmaster/${id}` : '/api/partmaster';
        await fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        closePartModal(); fetchPartMasters();
    });

    window.deletePartMaster = async (id) => {
        if (confirm('Delete this part master?')) {
            await fetch(`/api/partmaster/${id}`, { method: 'DELETE' });
            fetchPartMasters();
        }
    };
    window.editPartMaster = async (id) => {
        const res = await fetch('/api/partmaster'); const data = await res.json();
        const p = data.find(x => x.id === id);
        if (p) {
            document.getElementById('partId').value = p.id; document.getElementById('partFamily').value = p.family;
            document.getElementById('forgePn').value = p.forge_pn; document.getElementById('partno').value = p.partno;
            document.getElementById('partDept').value = p.department || '';
            document.getElementById('partVa').value = p.va || '';
            openPartModal(true);
        }
    };

    // --- PART OPERATIONS LOGIC ---
    let currentMachineOptions = '';
    
    function addOperationRow(op = { opn_no: '', description: '', machine: '', cycle_time: '' }) {
        const uniqueListId = 'machineList_' + Math.random().toString(36).substring(7);
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" class="opn-no" value="${op.opn_no}" style="width: 100%; padding: 8px;"></td>
            <td><input type="text" class="op-desc" value="${op.description}" style="width: 100%; padding: 8px;"></td>
            <td>
                <input type="text" class="op-mach" list="${uniqueListId}" placeholder="Type or select a Machine" style="width: 100%; padding: 8px;">
                <datalist id="${uniqueListId}">
                    ${currentMachineOptions}
                </datalist>
            </td>
            <td><input type="number" step="0.01" class="op-time" value="${op.cycle_time || ''}" style="width: 100%; padding: 8px;"></td>
        `;
        if (op.machine) tr.querySelector('.op-mach').value = op.machine;
        operationsBody.appendChild(tr);
    }

    document.getElementById('addOperationRowBtn').addEventListener('click', () => {
        addOperationRow();
    });

    window.openOperations = async (partId) => {
        operationsPartId.value = partId;
        
        // Get the part's department to filter machines
        const pRes = await fetch('/api/partmaster');
        const parts = await pRes.json();
        const part = parts.find(p => p.id === partId);
        const partDept = part ? (part.department || '').trim().toLowerCase() : '';

        // Ensure machines are loaded for dropdown
        if (availableMachines.length === 0) {
            const mRes = await fetch('/api/machines');
            availableMachines = await mRes.json();
        }

        // Fetch existing operations
        const res = await fetch(`/api/partmaster/${partId}/operations`);
        const existingOps = await res.json();

        operationsBody.innerHTML = '';
        currentMachineOptions = '<option value="">-- Select --</option>';
        availableMachines.forEach(m => {
            const mDept = (m.department || '').trim().toLowerCase();
            // Show if part has no dept, machine has no dept, or depts match
            if (!partDept || !mDept || mDept === partDept) {
                currentMachineOptions += `<option value="${m.name}">${m.name}</option>`;
            }
        });

        if (existingOps.length > 0) {
            existingOps.forEach(op => addOperationRow(op));
        } else {
            addOperationRow();
        }

        operationsModal.classList.add('show');
    };

    function closeOperationsModal() {
        operationsModal.classList.remove('show');
    }
    closeOperationsModalBtn.addEventListener('click', closeOperationsModal);
    cancelOperationsBtn.addEventListener('click', closeOperationsModal);

    saveOperationsBtn.addEventListener('click', async () => {
        const partId = operationsPartId.value;
        const rows = operationsBody.querySelectorAll('tr');
        const operationsData = [];

        rows.forEach(row => {
            const opn_no = row.querySelector('.opn-no').value.trim();
            const description = row.querySelector('.op-desc').value.trim();
            const machine = row.querySelector('.op-mach').value;
            const cycle_time = parseFloat(row.querySelector('.op-time').value) || 0;

            if (opn_no || description) {
                operationsData.push({
                    opn_no, description, machine, cycle_time
                });
            }
        });

        try {
            await fetch(`/api/partmaster/${partId}/operations`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(operationsData)
            });
            closeOperationsModal();
        } catch (e) {
            console.error('Error saving operations:', e);
        }
    });

    // --- MACHINES LOGIC ---
    async function fetchMachines() {
        try {
            const response = await fetch('/api/machines');
            const machines = await response.json();
            availableMachines = machines; // update global list
            machinesBody.innerHTML = '';
            if (machines.length === 0) {
                machinesBody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted)">No machines found.</td></tr>';
                return;
            }
            machines.forEach(m => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${m.id}</td><td>${m.department || ''}</td><td>${m.name}</td>
                    <td class="actions">
                        <button class="btn btn-edit" onclick="editMachine(${m.id})">Edit</button>
                        <button class="btn btn-danger" onclick="deleteMachine(${m.id})">Delete</button>
                    </td>`;
                machinesBody.appendChild(tr);
            });
        } catch (e) { console.error(e); }
    }

    function openMachineModal(isEdit) {
        machineModal.classList.add('show');
        machineModalTitle.textContent = isEdit ? 'Edit Machine' : 'Add Machine';
    }
    function closeMachineModal() { machineModal.classList.remove('show'); machineForm.reset(); document.getElementById('machineId').value = ''; }
    closeMachineBtn.addEventListener('click', closeMachineModal); cancelMachineBtn.addEventListener('click', closeMachineModal);

    machineForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('machineId').value;
        const data = { name: document.getElementById('machineName').value, department: document.getElementById('machineDept').value };
        const url = id ? `/api/machines/${id}` : '/api/machines';
        await fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        closeMachineModal(); fetchMachines();
    });

    window.deleteMachine = async (id) => {
        if (confirm('Delete this machine?')) {
            await fetch(`/api/machines/${id}`, { method: 'DELETE' });
            fetchMachines();
        }
    };
    window.editMachine = async (id) => {
        const res = await fetch('/api/machines'); const data = await res.json();
        const m = data.find(x => x.id === id);
        if (m) {
            document.getElementById('machineId').value = m.id; document.getElementById('machineName').value = m.name;
            document.getElementById('machineDept').value = m.department || '';
            openMachineModal(true);
        }
    };

    // --- OPERATORS LOGIC ---
    async function fetchOperators() {
        try {
            const response = await fetch('/api/operators');
            const operators = await response.json();
            operatorsBody.innerHTML = '';
            if (operators.length === 0) {
                operatorsBody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">No operators found.</td></tr>';
                return;
            }
            operators.forEach(o => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${o.id}</td><td>${o.department}</td><td>${o.name}</td>
                    <td class="actions">
                        <button class="btn btn-edit" onclick="editOperator(${o.id})">Edit</button>
                        <button class="btn btn-danger" onclick="deleteOperator(${o.id})">Delete</button>
                    </td>`;
                operatorsBody.appendChild(tr);
            });
        } catch (e) { console.error(e); }
    }

    function openOperatorModal(isEdit) {
        operatorModal.classList.add('show');
        operatorModalTitle.textContent = isEdit ? 'Edit Operator' : 'Add Operator';
    }
    function closeOperatorModal() { operatorModal.classList.remove('show'); operatorForm.reset(); document.getElementById('operatorId').value = ''; }
    closeOperatorBtn.addEventListener('click', closeOperatorModal); cancelOperatorBtn.addEventListener('click', closeOperatorModal);

    operatorForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('operatorId').value;
        const data = { name: document.getElementById('operatorName').value, department: document.getElementById('operatorDepartment').value };
        const url = id ? `/api/operators/${id}` : '/api/operators';
        await fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        closeOperatorModal(); fetchOperators();
    });

    window.deleteOperator = async (id) => {
        if (confirm('Delete this operator?')) {
            await fetch(`/api/operators/${id}`, { method: 'DELETE' });
            fetchOperators();
        }
    };
    window.editOperator = async (id) => {
        const res = await fetch('/api/operators'); const data = await res.json();
        const o = data.find(x => x.id === id);
        if (o) {
            document.getElementById('operatorId').value = o.id; 
            document.getElementById('operatorName').value = o.name;
            document.getElementById('operatorDepartment').value = o.department;
            openOperatorModal(true);
        }
    };

    // Initial fetch
    fetchProducts();
    // Pre-fetch machines so the dropdown is ready
    fetch('/api/machines').then(r => r.json()).then(data => availableMachines = data);

    // --- SCHEDULE LOGIC ---
    const schedulePartNo = document.getElementById('schedulePartNo');
    const scheduleDept = document.getElementById('scheduleDept');
    const scheduleCreateForm = document.getElementById('scheduleCreateForm');

    let allPartMasters = [];

    async function loadSchedulePartNos() {
        if (allPartMasters.length === 0) {
            const res = await fetch('/api/partmaster');
            allPartMasters = await res.json();
        }
        // Force trigger change to populate datalist if dept is already selected
        scheduleDept.dispatchEvent(new Event('change'));
    }

    scheduleDept.addEventListener('change', (e) => {
        const selectedDept = e.target.value;
        const datalist = document.getElementById('schedulePartNoList');
        if (!datalist) return;
        datalist.innerHTML = '';
        if (selectedDept) {
            const filteredParts = allPartMasters.filter(p => p.department === selectedDept);
            filteredParts.forEach(p => {
                datalist.innerHTML += `<option value="${p.partno}">`;
            });
        }
        schedulePartNo.value = ''; // Reset part no input when dept changes
    });

    async function fetchSchedulesForList() {
        try {
            const res = await fetch('/api/schedule');
            const schedules = await res.json();
            const tbody = document.getElementById('scheduleListBody');
            if (tbody) {
                tbody.innerHTML = '';
                if (schedules.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">No schedules found.</td></tr>';
                    return;
                }
                // Sort by newest first assuming higher ID means newer
                schedules.sort((a, b) => b.id - a.id);
                schedules.forEach(s => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${s.partno}</td>
                        <td>${s.target_date}</td>
                        <td>${s.qty}</td>
                        <td><span style="padding: 2px 8px; background-color: rgba(59, 130, 246, 0.1); color: var(--primary); border-radius: 12px; font-size: 0.85em;">${s.status || 'Pending'}</span></td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        } catch (e) {
            console.error('Error fetching schedules:', e);
        }
    }

    if (scheduleCreateForm) {
        scheduleCreateForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = {
                partno: schedulePartNo.value,
                department: scheduleDept.value,
                target_date: document.getElementById('scheduleTargetDate').value,
                qty: parseInt(document.getElementById('scheduleQty').value)
            };
            try {
                const response = await fetch('/api/schedule', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (response.ok) {
                    alert('Schedule created successfully!');
                    scheduleCreateForm.reset();
                    scheduleDept.value = ''; // Reset dept field
                    fetchSchedulesForList();
                } else {
                    alert('Error creating schedule.');
                }
            } catch (error) {
                console.error('Error:', error);
            }
        });
    }

    const clearScheduleBtn = document.getElementById('clearScheduleBtn');
    if (clearScheduleBtn) {
        clearScheduleBtn.addEventListener('click', async () => {
            if (confirm("Are you sure you want to completely clear the entire schedule? This action cannot be undone.")) {
                try {
                    const response = await fetch('/api/schedule', { method: 'DELETE' });
                    if (response.ok) {
                        fetchSchedulesForList();
                    } else {
                        alert('Error clearing schedules.');
                    }
                } catch (e) {
                    console.error(e);
                    alert('Error clearing schedules.');
                }
            }
        });
    }

    // Call fetchSchedulesForList when opening the create tab
    sidebarScheduleCreate.addEventListener('click', (e) => {
        fetchSchedulesForList();
    });

    async function fetchRunSchedule() {
        try {
            const res = await fetch('/api/schedule/run');
            const data = await res.json();
            const tbody = document.getElementById('scheduleRunBody');
            if (!tbody) return;
            tbody.innerHTML = '';
            
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--text-muted)">No pending schedules found to run.</td></tr>';
                return;
            }
            
            data.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${item.partno}</td>
                    <td>${item.opn_no}</td>
                    <td>${item.description}</td>
                    <td>${item.machine}</td>
                    <td>${item.qty}</td>
                    <td>${item.cycle_time}</td>
                    <td>${item.runtime}</td>
                    <td><span style="font-weight: 500;">${item.start_date}</span></td>
                    <td><span style="font-weight: 500;">${item.end_date}</span></td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error('Error fetching run schedule:', e);
        }
    }

    // --- SCHEDULE STATUS LOGIC ---
    let statusAllParts = [];
    
    document.getElementById('statusDeptSelect').addEventListener('change', fetchScheduleStatus);
    document.getElementById('exportStatusBtn').addEventListener('click', () => {
        const table = document.getElementById('statusTable');
        if (!table) return;
        const wb = XLSX.utils.table_to_book(table, {sheet: "Status"});
        XLSX.writeFile(wb, `Schedule_Status_${new Date().toISOString().slice(0,10)}.xlsx`);
    });
    
    async function initScheduleStatus() {
        try {
            if (statusAllParts.length === 0) {
                const partsRes = await fetch('/api/partmaster');
                statusAllParts = await partsRes.json();
            }
            
            const deptSelect = document.getElementById('statusDeptSelect');
            if (deptSelect.value) {
                fetchScheduleStatus();
            }
        } catch (e) {
            console.error('Error init schedule status', e);
        }
    }

    async function fetchScheduleStatus() {
        const dept = document.getElementById('statusDeptSelect').value;
        const tbody = document.getElementById('statusBody');
        tbody.innerHTML = '';
        if (!dept) return;

        try {
            const [schedRes, logRes] = await Promise.all([
                fetch('/api/schedule'),
                fetch('/api/prodlog')
            ]);
            
            const allSchedules = await schedRes.json();
            const allLogs = await logRes.json();
            
            const deptSchedules = allSchedules.filter(s => (s.department || '').trim().toUpperCase() === dept.trim().toUpperCase() && (s.status === 'Pending' || !s.status));
            const uniqueParts = [...new Set(deptSchedules.map(s => s.partno))];
            
            for (const partno of uniqueParts) {
                const partObj = statusAllParts.find(p => (p.partno || '').trim().toUpperCase() === (partno || '').trim().toUpperCase());
                if (!partObj) continue;
                
                const opsRes = await fetch(`/api/partmaster/${partObj.id}/operations`);
                const operations = await opsRes.json();
                
                // Sort operations numerically if possible
                operations.sort((a, b) => {
                    let numA = parseInt(a.opn_no) || 0;
                    let numB = parseInt(b.opn_no) || 0;
                    return numA - numB;
                });
                
                const partSchedules = deptSchedules.filter(s => s.partno === partno);
                const schedQty = partSchedules.reduce((sum, s) => sum + (s.qty || 0), 0);
                
                let rowHtml = `<td>${partno}</td><td>${schedQty}</td>`;
                
                // Opn 1 to 10
                for (let i = 0; i < 10; i++) {
                    if (i < operations.length) {
                        const currentOp = operations[i];
                        const nextOp = operations[i + 1];
                        
                        // Total produced for current op
                        const currentProd = allLogs.filter(l => l.partno === partno && l.opn_no === currentOp.opn_no).reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                        
                        // Total produced for next op
                        let nextProd = 0;
                        if (nextOp) {
                            nextProd = allLogs.filter(l => l.partno === partno && l.opn_no === nextOp.opn_no).reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                        } else {
                            nextProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'debur').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                        }
                        
                        let balance = currentProd - nextProd;
                        if (balance < 0) balance = 0;
                        rowHtml += `<td>${balance}</td>`;
                    } else {
                        rowHtml += `<td></td>`;
                    }
                }
                
                // fixed columns: debur, for ins, rework, nc, rfd
                const fixedOps = ['debur', 'for ins', 'rework', 'nc', 'rfd'];
                for (let i = 0; i < fixedOps.length; i++) {
                    const fOp = fixedOps[i];
                    const prod = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === fOp).reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                    
                    let nextFProd = 0;
                    if (fOp === 'debur') {
                        nextFProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'for ins').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                    } else if (fOp === 'for ins') {
                        nextFProd = allLogs.filter(l => l.partno === partno && ['rework', 'nc', 'rfd'].includes((l.opn_no || '').toLowerCase())).reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                    }
                    
                    let fBalance = prod - nextFProd;
                    if (fBalance < 0) fBalance = 0;
                    rowHtml += `<td>${fBalance || (prod === 0 ? '' : 0)}</td>`;
                }
                
                const tr = document.createElement('tr');
                tr.innerHTML = rowHtml;
                tbody.appendChild(tr);
            }
            
        } catch (e) {
            console.error('Error fetching schedule status', e);
        }
    }

    // --- DEBUR LOGIC ---
    let deburAllParts = [];
    let deburOperatorsLoaded = false;
    
    document.getElementById('deburDeptSelect').addEventListener('change', fetchDeburStatus);
    
    async function initDebur() {
        try {
            document.getElementById('deburDate').valueAsDate = new Date();
            
            if (deburAllParts.length === 0) {
                const partsRes = await fetch('/api/partmaster');
                deburAllParts = await partsRes.json();
            }
            if (!deburOperatorsLoaded) {
                const opRes = await fetch('/api/operators');
                const operators = await opRes.json();
                const sel = document.getElementById('deburOperator');
                operators.forEach(o => {
                    const opt = document.createElement('option');
                    opt.value = o.name;
                    opt.textContent = o.name;
                    sel.appendChild(opt);
                });
                deburOperatorsLoaded = true;
            }
            
            fetchDeburLogs();
            
            const deptSelect = document.getElementById('deburDeptSelect');
            if (deptSelect.value) {
                fetchDeburStatus();
            }
        } catch (e) {
            console.error('Error init debur', e);
        }
    }
    
    async function fetchDeburStatus() {
        const dept = document.getElementById('deburDeptSelect').value;
        const tbody = document.getElementById('deburPartsBody');
        tbody.innerHTML = '';
        if (!dept) {
            tbody.innerHTML = '<tr><td colspan="2" style="color:var(--text-muted); text-align:center;">Select a department</td></tr>';
            return;
        }

        try {
            const [schedRes, logRes] = await Promise.all([
                fetch('/api/schedule'),
                fetch('/api/prodlog')
            ]);
            
            const allSchedules = await schedRes.json();
            const allLogs = await logRes.json();
            
            const deptSchedules = allSchedules.filter(s => (s.department || '').trim().toUpperCase() === dept.trim().toUpperCase() && (s.status === 'Pending' || !s.status));
            const uniqueParts = [...new Set(deptSchedules.map(s => s.partno))];
            
            if (uniqueParts.length === 0) {
                tbody.innerHTML = '<tr><td colspan="2" style="color:var(--text-muted); text-align:center;">No pending parts for this department</td></tr>';
                return;
            }
            
            for (const partno of uniqueParts) {
                const partObj = deburAllParts.find(p => (p.partno || '').trim().toUpperCase() === (partno || '').trim().toUpperCase());
                if (!partObj) continue;
                
                const opsRes = await fetch(`/api/partmaster/${partObj.id}/operations`);
                const operations = await opsRes.json();
                
                if (operations.length === 0) continue;
                
                operations.sort((a, b) => (parseInt(a.opn_no) || 0) - (parseInt(b.opn_no) || 0));
                const lastOp = operations[operations.length - 1];
                
                const lastOpProd = allLogs.filter(l => l.partno === partno && l.opn_no === lastOp.opn_no).reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                const deburredProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'debur').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                
                const balance = lastOpProd - deburredProd;
                
                if (balance <= 0) continue;
                
                const tr = document.createElement('tr');
                tr.style.cursor = 'pointer';
                tr.innerHTML = `
                    <td>${partno}</td>
                    <td style="font-weight: 600; color: ${balance > 0 ? 'var(--primary-color)' : 'inherit'};">${balance}</td>
                `;
                tr.addEventListener('click', () => {
                    document.getElementById('deburPartNo').value = partno;
                });
                tbody.appendChild(tr);
            }
            
            if (tbody.children.length === 0) {
                tbody.innerHTML = '<tr><td colspan="2" style="color:var(--text-muted); text-align:center;">No parts pending debur</td></tr>';
            }
        } catch (e) {
            console.error('Error fetching debur status', e);
        }
    }
    
    document.getElementById('deburForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            dept: document.getElementById('deburDeptSelect').value,
            date: document.getElementById('deburDate').value,
            shift: '',
            setter: '',
            machine: '',
            operator: document.getElementById('deburOperator').value,
            partno: document.getElementById('deburPartNo').value,
            opn_no: 'debur', // Use debur as the operation
            description: '',
            runtime: parseFloat(document.getElementById('deburHours').value) || 0,
            target_qty: 0,
            prod_qty: parseInt(document.getElementById('deburQty').value) || 0,
            efficiency: 0,
            idle_hours: 0,
            idle_reason: ''
        };
        
        try {
            const res = await fetch('/api/prodlog', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                document.getElementById('deburHours').value = '';
                document.getElementById('deburQty').value = '';
                fetchDeburStatus(); // Refresh left side
                fetchDeburLogs();   // Refresh right side logs
            } else {
                alert("Failed to save debur log.");
            }
        } catch (e) {
            console.error(e);
            alert("Error saving debur log.");
        }
    });

    async function fetchDeburLogs() {
        try {
            const res = await fetch('/api/prodlog');
            const allLogs = await res.json();
            const deburLogs = allLogs.filter(l => (l.opn_no || '').toLowerCase() === 'debur');
            
            // Sort descending by ID or Date to show newest first
            deburLogs.sort((a, b) => b.id - a.id);
            
            const tbody = document.getElementById('deburLogsBody');
            tbody.innerHTML = '';
            
            if (deburLogs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">No debur logs found.</td></tr>';
                return;
            }
            
            // Show only recent 50 logs to keep UI snappy
            deburLogs.slice(0, 50).forEach(log => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${log.date}</td>
                    <td>${log.operator || ''}</td>
                    <td>${log.partno}</td>
                    <td>${log.run_time || ''}</td>
                    <td><span style="font-weight: 500;">${log.prod_qty || ''}</span></td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error('Error fetching debur logs:', e);
        }
    }

    // --- INSPECTION LOGIC ---
    let inspAllParts = [];
    let inspOperatorsLoaded = false;
    
    document.getElementById('inspDeptSelect').addEventListener('change', fetchInspectionStatus);
    
    async function initInspection() {
        try {
            document.getElementById('inspDate').valueAsDate = new Date();
            
            if (inspAllParts.length === 0) {
                const partsRes = await fetch('/api/partmaster');
                inspAllParts = await partsRes.json();
            }
            if (!inspOperatorsLoaded) {
                const opRes = await fetch('/api/operators');
                const operators = await opRes.json();
                const sel = document.getElementById('inspOperator');
                operators.forEach(o => {
                    const opt = document.createElement('option');
                    opt.value = o.name;
                    opt.textContent = o.name;
                    sel.appendChild(opt);
                });
                inspOperatorsLoaded = true;
            }
            
            fetchInspectionLogs();
            
            const deptSelect = document.getElementById('inspDeptSelect');
            if (deptSelect.value) {
                fetchInspectionStatus();
            }
        } catch (e) {
            console.error('Error init inspection', e);
        }
    }
    
    async function fetchInspectionStatus() {
        const dept = document.getElementById('inspDeptSelect').value;
        const tbody = document.getElementById('inspPartsBody');
        tbody.innerHTML = '';
        if (!dept) {
            tbody.innerHTML = '<tr><td colspan="2" style="color:var(--text-muted); text-align:center;">Select a department</td></tr>';
            return;
        }

        try {
            const [schedRes, logRes] = await Promise.all([
                fetch('/api/schedule'),
                fetch('/api/prodlog')
            ]);
            
            const allSchedules = await schedRes.json();
            const allLogs = await logRes.json();
            
            const deptSchedules = allSchedules.filter(s => (s.department || '').trim().toUpperCase() === dept.trim().toUpperCase() && (s.status === 'Pending' || !s.status));
            const uniqueParts = [...new Set(deptSchedules.map(s => s.partno))];
            
            if (uniqueParts.length === 0) {
                tbody.innerHTML = '<tr><td colspan="2" style="color:var(--text-muted); text-align:center;">No pending parts for this department</td></tr>';
                return;
            }
            
            for (const partno of uniqueParts) {
                const deburredTotal = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'debur').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                const forInsTotal = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'for ins').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                
                const balance = deburredTotal - forInsTotal;
                
                if (balance <= 0) continue; // Only show parts with positive balance for inspection
                
                const tr = document.createElement('tr');
                tr.style.cursor = 'pointer';
                tr.innerHTML = `
                    <td>${partno}</td>
                    <td style="font-weight: 600; color: var(--primary-color);">${balance}</td>
                `;
                tr.addEventListener('click', () => {
                    document.getElementById('inspPartNo').value = partno;
                });
                tbody.appendChild(tr);
            }
            
            if (tbody.children.length === 0) {
                tbody.innerHTML = '<tr><td colspan="2" style="color:var(--text-muted); text-align:center;">No parts pending inspection</td></tr>';
            }
        } catch (e) {
            console.error('Error fetching inspection status', e);
        }
    }
    
    document.getElementById('inspForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const date = document.getElementById('inspDate').value;
        const operator = document.getElementById('inspOperator').value;
        const partno = document.getElementById('inspPartNo').value;
        const runtime = parseFloat(document.getElementById('inspHours').value) || 0;
        const dept = document.getElementById('inspDeptSelect').value;
        
        const inspQty = parseInt(document.getElementById('inspQty').value) || 0;
        const reworkQty = parseInt(document.getElementById('inspRework').value) || 0;
        const ncQty = parseInt(document.getElementById('inspNC').value) || 0;
        const rfdQty = parseInt(document.getElementById('inspRFD').value) || 0;
        
        if (inspQty === 0) {
            alert("Total Inspected quantity cannot be zero.");
            return;
        }
        
        const createPayload = (opn_no, qty) => ({
            dept, date, shift: '', setter: '', machine: '',
            operator, partno, opn_no, description: '', runtime,
            target_qty: 0, prod_qty: qty, efficiency: 0,
            idle_hours: 0, idle_reason: ''
        });
        
        const payloads = [];
        payloads.push(createPayload('for ins', inspQty));
        if (reworkQty > 0) payloads.push(createPayload('rework', reworkQty));
        if (ncQty > 0) payloads.push(createPayload('nc', ncQty));
        if (rfdQty > 0) payloads.push(createPayload('rfd', rfdQty));
        
        try {
            let successCount = 0;
            for (const payload of payloads) {
                const res = await fetch('/api/prodlog', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) successCount++;
            }
            
            if (successCount === payloads.length) {
                document.getElementById('inspHours').value = '';
                document.getElementById('inspQty').value = '';
                document.getElementById('inspRework').value = '';
                document.getElementById('inspNC').value = '';
                document.getElementById('inspRFD').value = '';
                
                fetchInspectionStatus(); // Refresh left side
                fetchInspectionLogs();   // Refresh right side logs
            } else {
                alert("Failed to save some or all inspection logs.");
            }
        } catch (e) {
            console.error(e);
            alert("Error saving inspection log.");
        }
    });

    async function fetchInspectionLogs() {
        try {
            const res = await fetch('/api/prodlog');
            const allLogs = await res.json();
            const inspLogs = allLogs.filter(l => (l.opn_no || '').toLowerCase() === 'for ins');
            
            // Sort descending by ID or Date to show newest first
            inspLogs.sort((a, b) => b.id - a.id);
            
            const tbody = document.getElementById('inspLogsBody');
            tbody.innerHTML = '';
            
            if (inspLogs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">No inspection logs found.</td></tr>';
                return;
            }
            
            // Show only recent 50 logs to keep UI snappy
            inspLogs.slice(0, 50).forEach(log => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${log.date}</td>
                    <td>${log.operator || ''}</td>
                    <td>${log.partno}</td>
                    <td>${log.runtime || ''}</td>
                    <td><span style="font-weight: 500;">${log.prod_qty || ''}</span></td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error('Error fetching inspection logs:', e);
        }
    }

    // --- PROD LOG LOGIC ---
    let prodLogAllMachines = [];
    let prodLogAllOperators = [];
    let prodLogSchedules = [];
    let currentPartOperations = [];

    async function initProdLog() {
        document.getElementById('prodLogDate').valueAsDate = new Date();
        
        // Fetch dependencies
        const machRes = await fetch('/api/machines');
        prodLogAllMachines = await machRes.json();
        
        const opRes = await fetch('/api/operators');
        prodLogAllOperators = await opRes.json();
        
        const schedRes = await fetch('/api/schedule');
        const schedData = await schedRes.json();
        prodLogSchedules = schedData.filter(s => s.status === 'Pending' || !s.status);
        
        // Populate Schedule Parts with ALL active schedules initially
        const partList = document.getElementById('prodLogPartNoList');
        partList.innerHTML = '';
        const uniqueSchedParts = [...new Set(prodLogSchedules.map(s => s.partno))];
        uniqueSchedParts.forEach(p => {
            partList.innerHTML += `<option value="${p}">`;
        });
        
        fetchProdLogs();
    }

    document.getElementById('prodLogDept').addEventListener('change', (e) => {
        const dept = e.target.value.trim().toUpperCase();
        const machSelect = document.getElementById('prodLogMachine');
        const opSelect = document.getElementById('prodLogOperator');
        const partList = document.getElementById('prodLogPartNoList');
        
        machSelect.innerHTML = '<option value="">-- Select Machine --</option>';
        opSelect.innerHTML = '<option value="">-- Select Operator --</option>';
        document.getElementById('prodLogPartNo').value = '';
        partList.innerHTML = '';
        
        prodLogAllMachines.filter(m => (m.department || '').trim().toUpperCase() === dept).forEach(m => {
            machSelect.innerHTML += `<option value="${m.name}">${m.name}</option>`;
        });
        
        prodLogAllOperators.filter(o => (o.department || '').trim().toUpperCase() === dept).forEach(o => {
            opSelect.innerHTML += `<option value="${o.name}">${o.name}</option>`;
        });
        
        // Filter pending schedules by this department
        const deptSchedules = prodLogSchedules.filter(s => (s.department || '').trim().toUpperCase() === dept);
        const uniqueSchedParts = [...new Set(deptSchedules.map(s => s.partno))];
        uniqueSchedParts.forEach(p => {
            partList.innerHTML += `<option value="${p}">`;
        });
        
        // Reset dependent fields
        document.getElementById('prodLogOpnNo').innerHTML = '<option value="">-- Select Operation --</option>';
        document.getElementById('prodLogDescription').value = '';
        document.getElementById('prodLogCycleTime').value = '';
        recalcProdLog();
    });

    document.getElementById('prodLogPartNo').addEventListener('change', async (e) => {
        const partno = e.target.value;
        const opnSelect = document.getElementById('prodLogOpnNo');
        opnSelect.innerHTML = '<option value="">-- Select Operation --</option>';
        document.getElementById('prodLogDescription').value = '';
        document.getElementById('prodLogCycleTime').value = '';
        recalcProdLog();
        
        if (!partno) return;
        
        // Need part_id to get operations. Let's fetch partmaster and find the id.
        const res = await fetch('/api/partmaster');
        const allParts = await res.json();
        const part = allParts.find(p => String(p.partno).trim().toLowerCase() === String(partno).trim().toLowerCase());
        if (part) {
            const opRes = await fetch(`/api/partmaster/${part.id}/operations`);
            currentPartOperations = await opRes.json();
            currentPartOperations.forEach(op => {
                opnSelect.innerHTML += `<option value="${op.opn_no}">${op.opn_no}</option>`;
            });
        }
    });

    document.getElementById('prodLogOpnNo').addEventListener('change', (e) => {
        const opn_no = String(e.target.value).trim();
        const op = currentPartOperations.find(o => String(o.opn_no).trim() === opn_no);
        if (op) {
            document.getElementById('prodLogDescription').value = op.description || '';
            document.getElementById('prodLogCycleTime').value = op.cycle_time || 0;
            recalcProdLog();
        }
    });

    function recalcProdLog() {
        const runtime = parseFloat(document.getElementById('prodLogRuntime').value) || 0;
        const prodQty = parseFloat(document.getElementById('prodLogProdQty').value) || 0;
        const cycleTime = parseFloat(document.getElementById('prodLogCycleTime').value) || 0;
        
        let targetQty = 0;
        if (cycleTime > 0) {
            targetQty = (runtime * 60) / cycleTime;
            document.getElementById('prodLogTargetQty').value = Math.floor(targetQty);
        } else {
            document.getElementById('prodLogTargetQty').value = '';
        }
        
        if (targetQty > 0) {
            const eff = (prodQty / targetQty) * 100;
            document.getElementById('prodLogEfficiency').value = eff.toFixed(2);
        } else {
            document.getElementById('prodLogEfficiency').value = '';
        }
    }

    document.getElementById('prodLogRuntime').addEventListener('input', recalcProdLog);
    document.getElementById('prodLogProdQty').addEventListener('input', recalcProdLog);

    async function fetchProdLogs() {
        try {
            const res = await fetch('/api/prodlog');
            const data = await res.json();
            const tbody = document.getElementById('prodLogBody');
            tbody.innerHTML = '';
            data.forEach(log => {
                let totalIdle = log.idle_hours || 0;
                if (log.idle_hours_2) totalIdle += log.idle_hours_2;
                if (log.idle_hours_3) totalIdle += log.idle_hours_3;

                // Pre-fill a map with 0 for all specific reasons
                const idleMap = {
                    "No load": 0, "No Operator": 0, "Setting": 0, "Setup": 0,
                    "No power": 0, "Tool issue": 0, "Quality issue": 0,
                    "fixture issue": 0, "Machine bd": 0, "misc": 0,
                    "Npd": 0, "rework": 0, "no plan": 0, "setter": 0
                };

                if (log.idle_reason && idleMap[log.idle_reason] !== undefined) {
                    idleMap[log.idle_reason] += log.idle_hours || 0;
                }
                if (log.idle_reason_2 && idleMap[log.idle_reason_2] !== undefined) {
                    idleMap[log.idle_reason_2] += log.idle_hours_2 || 0;
                }
                if (log.idle_reason_3 && idleMap[log.idle_reason_3] !== undefined) {
                    idleMap[log.idle_reason_3] += log.idle_hours_3 || 0;
                }

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${log.date}</td>
                    <td>${log.dept}</td>
                    <td>${log.shift}</td>
                    <td>${log.setter || ''}</td>
                    <td>${log.partno}</td>
                    <td>${log.opn_no}</td>
                    <td>${log.description || ''}</td>
                    <td>${log.machine}</td>
                    <td>${log.operator || ''}</td>
                    <td>${log.multiple_mc || 1}</td>
                    <td>${log.cycle_time || ''}</td>
                    <td>${log.runtime || ''}</td>
                    <td>${log.target_qty || ''}</td>
                    <td><span style="font-weight:bold;color:var(--primary);">${log.prod_qty}</span></td>
                    <td>${log.efficiency}%</td>
                    <td><span style="font-weight:bold;">${totalIdle.toFixed(2)}</span></td>
                    <td>${idleMap["No load"] || ''}</td>
                    <td>${idleMap["No Operator"] || ''}</td>
                    <td>${idleMap["Setting"] || ''}</td>
                    <td>${idleMap["Setup"] || ''}</td>
                    <td>${idleMap["No power"] || ''}</td>
                    <td>${idleMap["Tool issue"] || ''}</td>
                    <td>${idleMap["Quality issue"] || ''}</td>
                    <td>${idleMap["fixture issue"] || ''}</td>
                    <td>${idleMap["Machine bd"] || ''}</td>
                    <td>${idleMap["misc"] || ''}</td>
                    <td>${idleMap["Npd"] || ''}</td>
                    <td>${idleMap["rework"] || ''}</td>
                    <td>${idleMap["no plan"] || ''}</td>
                    <td>${idleMap["setter"] || ''}</td>
                `;
                
                const actionTd = document.createElement('td');
                const delBtn = document.createElement('button');
                delBtn.className = 'btn-text';
                delBtn.style.color = 'var(--danger-color)';
                delBtn.textContent = 'Delete';
                delBtn.onclick = async () => {
                    if (confirm('Are you sure you want to delete this log?')) {
                        try {
                            const delRes = await fetch(`/api/prodlog/${log.id}`, { method: 'DELETE' });
                            if (delRes.ok) {
                                fetchProdLogs();
                            } else {
                                alert('Error deleting log.');
                            }
                        } catch (err) {
                            console.error(err);
                            alert('Error deleting log.');
                        }
                    }
                };
                actionTd.appendChild(delBtn);
                tr.appendChild(actionTd);
                
                tbody.appendChild(tr);
            });
        } catch (e) { console.error(e); }
    }

    const prodLogForm = document.getElementById('prodLogForm');
    if (prodLogForm) {
        prodLogForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = {
                dept: document.getElementById('prodLogDept').value,
                date: document.getElementById('prodLogDate').value,
                shift: document.getElementById('prodLogShift').value,
                setter: document.getElementById('prodLogSetter').value,
                machine: document.getElementById('prodLogMachine').value,
                operator: document.getElementById('prodLogOperator').value,
                multiple_mc: parseInt(document.getElementById('prodLogMultipleMc').value) || 1,
                partno: document.getElementById('prodLogPartNo').value,
                opn_no: document.getElementById('prodLogOpnNo').value,
                description: document.getElementById('prodLogDescription').value,
                runtime: parseFloat(document.getElementById('prodLogRuntime').value) || 0,
                target_qty: parseFloat(document.getElementById('prodLogTargetQty').value) || 0,
                prod_qty: parseFloat(document.getElementById('prodLogProdQty').value) || 0,
                efficiency: parseFloat(document.getElementById('prodLogEfficiency').value) || 0,
                idle_hours: parseFloat(document.getElementById('prodLogIdleHours').value) || 0,
                idle_reason: document.getElementById('prodLogIdleReason').value,
                idle_hours_2: parseFloat(document.getElementById('prodLogIdleHours2').value) || 0,
                idle_reason_2: document.getElementById('prodLogIdleReason2').value,
                idle_hours_3: parseFloat(document.getElementById('prodLogIdleHours3').value) || 0,
                idle_reason_3: document.getElementById('prodLogIdleReason3').value
            };
            
            try {
                const response = await fetch('/api/prodlog', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (response.ok) {
                    alert('Production Log saved!');
                    prodLogForm.reset();
                    document.getElementById('prodLogDate').valueAsDate = new Date(); // reset date
                    fetchProdLogs();
                } else {
                    alert('Error saving Prod Log');
                }
            } catch (err) { console.error(err); }
        });
    }

    const exportProdLogBtn = document.getElementById('exportProdLogBtn');
    if (exportProdLogBtn) {
        exportProdLogBtn.addEventListener('click', () => {
            const table = document.getElementById('prodLogTable');
            if (!table) return;
            const wb = XLSX.utils.table_to_book(table, {sheet: "Prod Logs"});
            XLSX.writeFile(wb, `Production_Logs_${new Date().toISOString().slice(0,10)}.xlsx`);
        });
    }

    // --- RM Logs Fetch Logic ---
    async function fetchRmLogs(type) {
        try {
            const res = await fetch('/api/rawmateriallogs');
            const logs = await res.json();
            const filteredLogs = logs.filter(l => l.type === type);
            filteredLogs.sort((a, b) => new Date(b.date) - new Date(a.date));
            
            const tbodyId = type === 'receipt' ? 'rmReceiptBody' : 'rmDespatchBody';
            const tbody = document.getElementById(tbodyId);
            if (tbody) {
                tbody.innerHTML = '';
                filteredLogs.forEach(log => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${log.date}</td>
                        <td>${log.forge_pn}</td>
                        <td>${log.qty}</td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        } catch (e) {
            console.error(e);
        }
    }

    // --- RAW MATERIAL LOGIC ---
    let allRawMaterials = [];
    async function fetchRawMaterials() {
        try {
            const res = await fetch('/api/rawmaterials');
            allRawMaterials = await res.json();
            const tbody = document.getElementById('rawMaterialsBody');
            if (tbody) {
                tbody.innerHTML = '';
                allRawMaterials.forEach(rm => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${rm.forge_pn}</td>
                        <td>${rm.receipt}</td>
                        <td>${rm.despatch}</td>
                        <td>${rm.stock}</td>
                        <td class="action-col">
                            <button class="btn btn-primary btn-sm" onclick="editRawMaterial(${rm.id})">Edit</button>
                            <button class="btn btn-danger btn-sm" onclick="deleteRawMaterial(${rm.id})">Delete</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        } catch (e) {
            console.error('Error fetching raw materials', e);
        }
    }

    const rawMaterialModal = document.getElementById('rawMaterialModal');
    const rawMaterialForm = document.getElementById('rawMaterialForm');
    if (rawMaterialForm) {
        rawMaterialForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('rmId').value;
            const forge_pn = document.getElementById('rmForgePn').value;
            const quantity = parseInt(document.getElementById('rmQuantity').value) || 0;
            const despatch = parseInt(document.getElementById('rmDespatch').value) || 0;
            
            // Map quantity to receipt, stock is receipt - despatch
            const receipt = quantity;
            const stock = receipt - despatch;
            
            const payload = { forge_pn, receipt, despatch, stock };
            
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/rawmaterials/${id}` : '/api/rawmaterials';
            
            try {
                const res = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    rawMaterialModal.classList.remove('show');
                    fetchRawMaterials();
                } else {
                    alert('Failed to save raw material');
                }
            } catch (e) {
                console.error(e);
            }
        });
        
        document.getElementById('closeRmModalBtn').addEventListener('click', () => {
            rawMaterialModal.classList.remove('show');
        });
        document.getElementById('cancelRmBtn').addEventListener('click', () => {
            rawMaterialModal.classList.remove('show');
        });
    }

    const rmLogModal = document.getElementById('rmLogModal');
    const rmLogForm = document.getElementById('rmLogForm');
    if (rmLogForm) {
        rmLogForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const type = document.getElementById('rmLogType').value;
            const date = document.getElementById('rmLogDate').value;
            const forge_pn = document.getElementById('rmLogForgePn').value;
            const qty = parseInt(document.getElementById('rmLogQty').value) || 0;
            
            const payload = { type, date, forge_pn, qty };
            
            try {
                const res = await fetch('/api/rawmateriallogs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    rmLogModal.classList.remove('show');
                    fetchRmLogs(type);
                } else {
                    alert('Failed to save log');
                }
            } catch (e) {
                console.error(e);
            }
        });
        
        document.getElementById('closeRmLogModalBtn').addEventListener('click', () => {
            rmLogModal.classList.remove('show');
        });
        document.getElementById('cancelRmLogBtn').addEventListener('click', () => {
            rmLogModal.classList.remove('show');
        });
    }

    window.editRawMaterial = (id) => {
        const rm = allRawMaterials.find(r => r.id === id);
        if (rm) {
            document.getElementById('rmModalTitle').innerText = 'Edit Raw Material';
            document.getElementById('rmId').value = rm.id;
            document.getElementById('rmForgePn').value = rm.forge_pn;
            document.getElementById('rmQuantity').value = rm.receipt;
            document.getElementById('rmDespatch').value = rm.despatch;
            rawMaterialModal.classList.add('show');
        }
    };

    window.deleteRawMaterial = async (id) => {
        if (confirm('Are you sure you want to delete this raw material?')) {
            try {
                const res = await fetch(`/api/rawmaterials/${id}`, { method: 'DELETE' });
                if (res.ok) fetchRawMaterials();
            } catch (e) {
                console.error(e);
            }
        }
    };


    // --- USER MANAGEMENT LOGIC ---
    async function fetchUsers() {
        try {
            const res = await fetch('/api/users');
            const users = await res.json();
            const tbody = document.getElementById('usersBody');
            if (!tbody) return;
            tbody.innerHTML = '';
            users.forEach(u => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${u.id}</td>
                    <td>${u.username}</td>
                    <td>${u.role}</td>
                    <td>
                        <button class="btn btn-danger" onclick="deleteUser(${u.id})">Delete</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) { console.error(e); }
    }
    
    // --- RM REQUIREMENT REPORT ---
    async function fetchRmRequirement() {
        try {
            const [schedRes, pmRes, rmRes] = await Promise.all([
                fetch('/api/schedule'),
                fetch('/api/partmaster'),
                fetch('/api/rawmaterials')
            ]);
            
            const schedules = await schedRes.json();
            const partMasters = await pmRes.json();
            const rawMaterials = await rmRes.json();
            
            const reqs = {};
            // Only consider Pending schedules for requirement calculation
            const pendingSchedules = schedules.filter(s => s.status === 'Pending' || !s.status);
            
            pendingSchedules.forEach(sched => {
                const part = partMasters.find(p => p.partno === sched.partno);
                if (part && part.forge_pn) {
                    const fpn = part.forge_pn.trim().toUpperCase();
                    reqs[fpn] = (reqs[fpn] || 0) + (sched.qty || 0);
                }
            });
            
            const tbody = document.getElementById('rmRequirementBody');
            if (tbody) {
                tbody.innerHTML = '';
                const keys = Object.keys(reqs).sort();
                
                if (keys.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">No pending schedules found to generate requirement report.</td></tr>';
                    return;
                }
                
                keys.forEach(fpn => {
                    const required = reqs[fpn];
                    const rm = rawMaterials.find(r => (r.forge_pn || '').trim().toUpperCase() === fpn);
                    const stock = rm ? (rm.stock || 0) : 0;
                    const shortage = Math.max(0, required - stock);
                    
                    if (shortage <= 0) return; // Display only parts with an actual shortage
                    
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${fpn}</td>
                        <td>${required}</td>
                        <td>${stock}</td>
                        <td style="font-weight: 600; color: ${shortage > 0 ? '#ef4444' : 'inherit'};">${shortage}</td>
                    `;
                    tbody.appendChild(tr);
                });
                
                if (tbody.children.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">No parts with shortage found.</td></tr>';
                }
            }
        } catch (e) {
            console.error('Error fetching RM Requirement', e);
        }
    }
    
    const exportRmReqBtn = document.getElementById('exportRmReqBtn');
    if (exportRmReqBtn) {
        exportRmReqBtn.addEventListener('click', () => {
            const table = document.getElementById('rmRequirementTable');
            if (table) {
                const wb = XLSX.utils.table_to_book(table, { sheet: "RM Requirement" });
                XLSX.writeFile(wb, "RM_Requirement_Report.xlsx");
            }
        });
    }
    
    window.deleteUser = async (id) => {
        if (confirm('Delete this user?')) {
            try {
                const res = await fetch(`/api/users/${id}`, { method: 'DELETE' });
                if (res.ok) fetchUsers();
                else alert('Failed to delete user.');
            } catch (e) { console.error(e); }
        }
    };

    const userCreateForm = document.getElementById('userCreateForm');
    if (userCreateForm) {
        userCreateForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('userName').value;
            const password = document.getElementById('userPass').value;
            
            // Collect checked screens
            const checkboxes = document.querySelectorAll('#userScreensList input[type="checkbox"]:checked');
            const screens = Array.from(checkboxes).map(cb => cb.value);
            
            try {
                const res = await fetch('/api/users', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username,
                        password,
                        accessible_screens: JSON.stringify(screens)
                    })
                });
                if (res.ok) {
                    alert('User created!');
                    userCreateForm.reset();
                    fetchUsers();
                } else {
                    const err = await res.json();
                    alert(err.detail || 'Error creating user');
                }
            } catch (err) {
                console.error(err);
                alert('Error creating user');
            }
        });
    }

});
