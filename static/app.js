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
        loginOverlay.style.display = 'flex';
    } else {
        loginOverlay.style.display = 'none';
        appContainer.style.display = '';
        
        // Access Control Logic
        const allTabs = document.querySelectorAll('[data-screen]');
        let firstAvailableTab = null;
        let accessibleScreens = [];
        try {
            accessibleScreens = JSON.parse(userObj.accessible_screens || '[]');
        } catch(e) {}
        
        allTabs.forEach(tab => {
            const screen = tab.getAttribute('data-screen');
            const isAllowed = userObj.role === 'admin' || accessibleScreens.includes(screen) || ((screen === 'rawmaterial' || screen === 'ht') && (accessibleScreens.includes('inventory') || accessibleScreens.includes('rawmaterial'))) || (screen === 'attendance' && accessibleScreens.includes('hr'));
            if (isAllowed) {
                tab.style.display = 'inline-block';
                if (!firstAvailableTab) firstAvailableTab = tab;
            } else {
                tab.style.display = 'none';
            }
        });

        // Main tabs access control
        document.querySelectorAll('.main-tab[data-group]').forEach(tab => {
            const group = tab.getAttribute('data-group');
            if (userObj.role === 'admin') {
                tab.style.display = 'inline-block';
            } else {
                const groupScreens = {
                    'master': ['partmaster', 'machines', 'operators', 'dept', 'shift', 'vendors', 'setters'],
                    'inventory': ['inventory', 'rawmaterial', 'ht'],
                    'production': ['schedule', 'status', 'prodlog', 'debur'],
                    'toolcrib': ['insertmaster', 'drillmaster', 'products'],
                    'reports': ['reports'],
                    'maintenance': ['maintenance', 'bdslip'],
                    'hr': ['hr', 'attendance']
                };
                const allowed = groupScreens[group] ? groupScreens[group].some(s => accessibleScreens.includes(s)) : false;
                tab.style.display = allowed ? 'inline-block' : 'none';
            }
        });
        
        // Special case for Users tab
        const sidebarUsers = document.getElementById('sidebarUsers');
        if (sidebarUsers) {
            if (userObj.role === 'admin') {
                sidebarUsers.style.display = 'inline-block';
            } else {
                sidebarUsers.style.display = 'none';
            }
        }

        // Add logout button to header actions div
        const actionDiv = document.getElementById('headerActions');
        if (actionDiv && !document.getElementById('logoutBtn')) {
            const logoutBtn = document.createElement('button');
            logoutBtn.id = 'logoutBtn';
            logoutBtn.className = 'btn btn-secondary';
            logoutBtn.textContent = `Logout (${userObj.username})`;
            logoutBtn.onclick = () => {
                localStorage.removeItem('grs_user');
                window.location.reload();
            };
            actionDiv.appendChild(logoutBtn);
        }

        // Auto-click the first available tab if they don't have access to the default (products)
        if (userObj.role !== 'admin' && firstAvailableTab && !accessibleScreens.includes('products')) {
            setTimeout(() => {
                firstAvailableTab.click();
            }, 100);
        }
    }

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (loginError) loginError.style.display = 'none';
            const usernameInput = document.getElementById('loginUsername');
            const passwordInput = document.getElementById('loginPassword');
            const username = usernameInput ? usernameInput.value : '';
            const password = passwordInput ? passwordInput.value : '';
            
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
                    if (loginError) loginError.style.display = 'block';
                }
            } catch (err) {
                console.error(err);
                if (loginError) loginError.style.display = 'block';
            }
        });
    }

    // Shared
    const addBtn = document.getElementById('addBtn');
    const importBtn = document.getElementById('importBtn');
    const importFile = document.getElementById('importFile');
    let currentTab = 'products';
    let availableMachines = [];
    let allRawMaterials = [];
    let rmLogForgePnSelect = null;
    let rmLogFinishPartNoSelect = null;
    let globalPartMasters = [];
    let allShifts = [];
    let currentOperatorSessionHours = 0;

    // Tabs
    const tabRawMaterial = document.getElementById('tabRawMaterial');
    const sidebarRmMaster = document.getElementById('sidebarRmMaster');
    const sidebarRmReceipt = document.getElementById('sidebarRmReceipt');
    const sidebarRmDespatch = document.getElementById('sidebarRmDespatch');
    
    const sidebarProducts = document.getElementById('sidebarProducts');
    const sidebarPartMaster = document.getElementById('sidebarPartMaster');
    const sidebarMachines = document.getElementById('sidebarMachines');
    const sidebarOperators = document.getElementById('sidebarOperators');
    const sidebarDept = document.getElementById('sidebarDept');
    const sidebarShift = document.getElementById('sidebarShift');
    const sidebarVendors = document.getElementById('sidebarVendors');
    const sidebarSetters = document.getElementById('sidebarSetters');
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
    const departmentsSection = document.getElementById('departmentsSection');
    const shiftsSection = document.getElementById('shiftsSection');
    const vendorsSection = document.getElementById('vendorsSection');
    const settersSection = document.getElementById('settersSection');
    const htSection = document.getElementById('htSection');
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

    const deptModal = document.getElementById('deptModal');
    const deptForm = document.getElementById('deptForm');
    const cancelDeptBtn = document.getElementById('cancelDeptBtn');
    const deptIdInput = document.getElementById('deptId');
    const deptNameInput = document.getElementById('deptName');
    const deptModalTitle = document.getElementById('deptModalTitle');

    const shiftModal = document.getElementById('shiftModal');
    const shiftForm = document.getElementById('shiftForm');
    const cancelShiftBtn = document.getElementById('cancelShiftBtn');
    const shiftIdInput = document.getElementById('shiftId');
    const shiftNameInput = document.getElementById('shiftName');
    const shiftHoursInput = document.getElementById('shiftHours');
    const shiftModalTitle = document.getElementById('shiftModalTitle');


    function hideAllSections() {
        const sections = [
            'usersSection', 'reportsSection', 'rmRequirementSection', 'mcUtilSection', 'operEffSection',
            'rawMaterialsSection', 'rmReceiptSection', 'rmDespatchSection',
            'productsSection', 'insertMasterSection', 'drillMasterSection', 'insertReceiptSection', 'insertIssueSection', 'partMasterSection', 'machinesSection',
            'operatorsSection', 'departmentsSection', 'shiftsSection', 'vendorsSection', 'settersSection', 'htSection', 'scheduleCreateSection', 'scheduleRunSection',
            'scheduleStatusSection', 'prodLogSection', 'deburSection',
            'inspectionSection', 'maintenanceSection', 'bdSlipSection', 'serviceDetailsSection', 'hrSection', 'attendanceSection'
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
                let submenu = document.getElementById('submenu' + group.charAt(0).toUpperCase() + group.slice(1));
                if (!submenu) {
                    submenu = Array.from(document.querySelectorAll('.sub-group')).find(el => el.id.toLowerCase() === ('submenu' + group).toLowerCase());
                }
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
        'sidebarDept': { tab: 'dept', action: () => {
            departmentsSection.style.display = 'block';
            importBtn.style.display = 'none';
            addBtn.style.display = 'inline-flex';
            addBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Dept';
            fetchDepartments();
        }},
        'sidebarShift': { tab: 'shift', action: () => {
            if (shiftsSection) shiftsSection.style.display = 'block';
            importBtn.style.display = 'none';
            addBtn.style.display = 'inline-flex';
            addBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Shift';
            fetchShifts();
        }},
        'sidebarVendors': { tab: 'vendors', action: () => {
            if (vendorsSection) vendorsSection.style.display = 'block';
            importBtn.style.display = 'none';
            addBtn.style.display = 'inline-flex';
            addBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Vendor';
            fetchVendors();
        }},
        'sidebarSetters': { tab: 'setters', action: () => {
            if (settersSection) settersSection.style.display = 'block';
            importBtn.style.display = 'none';
            addBtn.style.display = 'inline-flex';
            addBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Setter';
            fetchSetters();
        }},
        'sidebarHt': { tab: 'ht', action: () => {
            if (htSection) htSection.style.display = 'block';
            importBtn.style.display = 'none';
            addBtn.style.display = 'inline-flex';
            addBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Send to HT';
            fetchHtData();
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
            if (scheduleCreateSection) scheduleCreateSection.style.display = 'block';
            addBtn.style.display = 'none';
            fetchSchedulesForList();
        }},
        'sidebarMcUtil': { tab: 'mc_util', action: () => { 
            const mcUtilSec = document.getElementById('mcUtilSection');
            if (mcUtilSec) mcUtilSec.style.display = 'block';
            addBtn.style.display = 'none';
            // Set default dates if empty
            if (!document.getElementById('mcUtilToDate').value) {
                const today = new Date().toISOString().split('T')[0];
                document.getElementById('mcUtilToDate').value = today;
                document.getElementById('mcUtilFromDate').value = new Date(Date.now() - 30*24*60*60*1000).toISOString().split('T')[0];
            }
        }},
        'sidebarInsertMaster': { tab: 'insertmaster', action: () => {
            const sec = document.getElementById('insertMasterSection');
            if (sec) sec.style.display = 'block';
            importBtn.style.display = 'inline-block';
            addBtn.style.display = 'none';
            fetchInsertMasters();
        }},
        'sidebarDrillMaster': { tab: 'drillmaster', action: () => {
            const sec = document.getElementById('drillMasterSection');
            if (sec) sec.style.display = 'block';
            importBtn.style.display = 'inline-block';
            addBtn.style.display = 'none';
            fetchDrillMasters();
        }},
        'sidebarInsertReceipt': { tab: 'insertreceipt', action: () => {
            const sec = document.getElementById('insertReceiptSection');
            if (sec) sec.style.display = 'block';
            importBtn.style.display = 'inline-block';
            addBtn.style.display = 'none';
            fetchInsertReceipts();
        }},
        'sidebarInsertIssue': { tab: 'insertissue', action: () => {
            const sec = document.getElementById('insertIssueSection');
            if (sec) sec.style.display = 'block';
            importBtn.style.display = 'inline-block';
            addBtn.style.display = 'none';
            fetchInsertIssues();
        }},
        'sidebarOperEff': { tab: 'oper_eff', action: () => {
            const operEffSec = document.getElementById('operEffSection');
            if (operEffSec) operEffSec.style.display = 'block';
            addBtn.style.display = 'none';
            if (!document.getElementById('operEffDate').value) {
                const today = new Date().toISOString().split('T')[0];
                document.getElementById('operEffDate').value = today;
            }
            fetchOperEffReport();
        }},
        'sidebarScheduleCreate': { tab: 'schedule_create', action: () => { 
            scheduleCreateSection.style.display = 'block'; 
            addBtn.style.display = 'none'; 
            fetchScheduleOptions(); 
        }},
        'sidebarScheduleRun': { tab: 'schedule_run', action: () => { 
            scheduleRunSection.style.display = 'block'; 
            addBtn.style.display = 'none'; 
            fetchRunSchedule(); 
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
        }},
        'sidebarAttendance': { tab: 'attendance', action: () => {
            const attSec = document.getElementById('attendanceSection');
            if (attSec) attSec.style.display = 'block';
            addBtn.style.display = 'none';
            initAttendance();
        }},
        'sidebarBdSlip': { tab: 'bdslip', action: () => {
            const bdSec = document.getElementById('bdSlipSection');
            if (bdSec) bdSec.style.display = 'block';
            addBtn.style.display = 'none';
            fetchBdSlips();
        }},
        'sidebarServiceDetails': { tab: 'servicedetails', action: () => {
            const sdSec = document.getElementById('serviceDetailsSection');
            if (sdSec) sdSec.style.display = 'block';
            addBtn.style.display = 'none';
            initServiceDetails();
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

    addBtn.addEventListener('click', async () => {
        if (currentTab === 'products') openProductModal(false);
        else if (currentTab === 'partmaster') openPartModal(false);
        else if (currentTab === 'machines') openMachineModal(false);
        else if (currentTab === 'operators') openOperatorModal(false);
        else if (currentTab === 'dept') openDeptModal();
        else if (currentTab === 'shift') openShiftModal();
        else if (currentTab === 'vendors') openVendorModal();
        else if (currentTab === 'setters') openSetterModal(false);
        else if (currentTab === 'ht') openHtModal();
        else if (currentTab === 'rawmaterial') {
            document.getElementById('rmModalTitle').innerText = 'Add Raw Material';
            document.getElementById('rawMaterialForm').reset();
            document.getElementById('rmId').value = '';
            document.getElementById('rawMaterialModal').classList.add('show');
        }
        else if (currentTab === 'rm_receipt' || currentTab === 'rm_despatch') {
            const isReceipt = currentTab === 'rm_receipt';
            document.getElementById('rmLogModalTitle').innerText = isReceipt ? 'Add Receipt' : 'Add Despatch';
            const savedDate = document.getElementById('rmLogDate').value;
            document.getElementById('rmLogForm').reset();
            if (savedDate) document.getElementById('rmLogDate').value = savedDate;
            else document.getElementById('rmLogDate').valueAsDate = new Date();
            document.getElementById('rmLogType').value = isReceipt ? 'receipt' : 'despatch';
            
            // Fetch if empty
            if (allRawMaterials.length === 0) {
                const rRes = await fetch('/api/rawmaterials');
                allRawMaterials = await rRes.json();
            }

            // Populate select with forge PNs
            const selectEl = document.getElementById('rmLogForgePn');
            selectEl.innerHTML = '<option value="">-- Select Forge PN --</option>';
            allRawMaterials.forEach(rm => {
                const opt = document.createElement('option');
                opt.value = rm.forge_pn;
                opt.textContent = rm.forge_pn;
                selectEl.appendChild(opt);
            });
            
            if (rmLogForgePnSelect) {
                rmLogForgePnSelect.destroy();
            }
            rmLogForgePnSelect = new TomSelect(selectEl, {
                create: true,
                sortField: { field: "text", direction: "asc" }
            });
            
            if (isReceipt) {
                document.getElementById('rmLogDcNoGroup').style.display = 'none';
                document.getElementById('rmLogFinishPartNoGroup').style.display = 'none';
            } else {
                document.getElementById('rmLogDcNoGroup').style.display = 'block';
                document.getElementById('rmLogFinishPartNoGroup').style.display = 'block';
                
                if (globalPartMasters.length === 0) {
                    const pmRes = await fetch('/api/partmaster');
                    globalPartMasters = await pmRes.json();
                }
                
                const fpSelectEl = document.getElementById('rmLogFinishPartNo');
                fpSelectEl.innerHTML = '<option value="">-- Select Finish Part No --</option>';
                globalPartMasters.forEach(pm => {
                    const opt = document.createElement('option');
                    opt.value = pm.partno;
                    opt.textContent = pm.partno;
                    fpSelectEl.appendChild(opt);
                });
                
                if (rmLogFinishPartNoSelect) {
                    rmLogFinishPartNoSelect.destroy();
                }
                rmLogFinishPartNoSelect = new TomSelect(fpSelectEl, {
                    create: false,
                    sortField: { field: "text", direction: "asc" }
                });
                
                rmLogFinishPartNoSelect.on('change', (val) => {
                    if (!val) return;
                    const selected = globalPartMasters.find(p => p.partno === val);
                    if (selected && selected.forge_pn && rmLogForgePnSelect) {
                        rmLogForgePnSelect.setValue(selected.forge_pn);
                    }
                });
            }
            
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
                        let partno = '', family = '', forge_pn = '', department = '', va = '';
                        let opn_no = '', description = '', machine = '', cycle_time = 0;
                        for (let k in row) {
                            let key = k.toLowerCase().replace(/[^a-z0-9]/g, '');
                            let val = String(row[k]).trim();
                            if (key === 'partno') partno = val;
                            else if (key === 'family') family = val;
                            else if (key === 'forgepn') forge_pn = val;
                            else if (key === 'dept' || key === 'department') department = val;
                            else if (key === 'va') va = val;
                            else if (key === 'opnno') opn_no = val;
                            else if (key === 'description') description = val;
                            else if (key === 'machine') machine = val;
                            else if (key === 'cycletime') cycle_time = parseFloat(val) || 0;
                        }
                        if (!partno) return;

                        if (!partsMap[partno]) {
                            partsMap[partno] = {
                                family, forge_pn, partno, department, va, operations: []
                            };
                        }

                        if (opn_no || description) {
                            partsMap[partno].operations.push({
                                opn_no, description, machine, cycle_time
                            });
                        }
                    });
                    endpoint = '/api/partmaster/bulk_import';
                    bodyData = JSON.stringify({ parts: Object.values(partsMap) });
                } else if (currentTab === 'machines') {
                    const machines = [];
                    json.forEach(row => {
                        let name = '';
                        let dept = '';
                        for (let k in row) {
                            let key = k.toLowerCase().replace(/[^a-z0-9]/g, '');
                            if (key === 'machinename' || key === 'machine' || key === 'name') name = String(row[k]).trim();
                            if (key === 'dept' || key === 'department') dept = String(row[k]).trim();
                        }
                        if (!name) return;
                        machines.push({
                            name: name,
                            department: dept
                        });
                    });
                    endpoint = '/api/machines/bulk_import';
                    bodyData = JSON.stringify({ machines: machines });
                } else if (currentTab === 'operators') {
                    const operators = [];
                    json.forEach(row => {
                        let name = '';
                        let dept = '';
                        let desig = 'Operator';
                        for (let k in row) {
                            let key = k.toLowerCase().replace(/[^a-z0-9]/g, '');
                            if (key === 'name' || key === 'operatorname' || key === 'operator') name = String(row[k]).trim();
                            if (key === 'dept' || key === 'department') dept = String(row[k]).trim();
                            if (key === 'designation' || key === 'desig' || key === 'role') desig = String(row[k]).trim();
                        }
                        if (!name) return;
                        operators.push({
                            name: name,
                            department: dept,
                            designation: desig || 'Operator'
                        });
                    });
                    endpoint = '/api/operators/bulk_import';
                    bodyData = JSON.stringify({ operators: operators });
                } else if (currentTab === 'rawmaterial') {
                    const rawmaterials = [];
                    json.forEach(row => {
                        let forge_pn = '', quantity = 0;
                        for (let k in row) {
                            let key = k.toLowerCase().replace(/[^a-z0-9]/g, '');
                            let val = String(row[k]).trim();
                            if (key === 'forgepn') forge_pn = val;
                            else if (key === 'quantity' || key === 'qty' || key === 'stock' || key === 'receipt') quantity = parseInt(val) || 0;
                        }
                        if (!forge_pn) return;
                        rawmaterials.push({ forge_pn, receipt: quantity, despatch: 0, stock: quantity });
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
                        let forge_pn = '', qty = 0, date = '';
                        for (let k in row) {
                            let key = k.toLowerCase().replace(/[^a-z0-9]/g, '');
                            let val = String(row[k]).trim();
                            if (key === 'forgepn') forge_pn = val;
                            else if (key === 'quantity' || key === 'qty') qty = parseInt(val) || 0;
                            else if (key === 'date') date = row[k];
                        }
                        if (!forge_pn || qty <= 0) return;
                        
                        if (!date) {
                            date = new Date().toISOString().split('T')[0];
                        } else {
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
                partMasterBody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted)">No part masters found.</td></tr>';
                return;
            }
            parts.forEach(p => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${p.id}</td><td>${p.customer || ''}</td><td>${p.department || ''}</td><td>${p.family}</td><td>${p.forge_pn}</td><td>${p.partno}</td><td>${p.va || ''}</td>
                    <td class="actions">
                        <button class="btn btn-outline" style="margin-right: 5px;" onclick="openOperations(${p.id})">Operations</button>
                        <button class="btn btn-edit" onclick="editPartMaster(${p.id})">Edit</button>
                        <button class="btn btn-danger" onclick="deletePartMaster(${p.id})">Delete</button>
                    </td>`;
                partMasterBody.appendChild(tr);
            });
            applyPartMasterHeaderFilters();
        } catch (e) { console.error(e); }
    }

    function applyPartMasterHeaderFilters() {
        const filters = {};
        document.querySelectorAll('.part-master-col-filter').forEach(input => {
            const val = input.value.trim().toLowerCase();
            if (val) {
                filters[input.getAttribute('data-col')] = val;
            }
        });

        const rows = document.querySelectorAll('#partMasterBody tr');
        rows.forEach(tr => {
            const cells = tr.children;
            let show = true;
            for (const colIdx in filters) {
                const cell = cells[parseInt(colIdx)];
                if (cell) {
                    const cellText = (cell.textContent || '').trim().toLowerCase();
                    if (!cellText.includes(filters[colIdx])) {
                        show = false;
                        break;
                    }
                }
            }
            tr.style.display = show ? '' : 'none';
        });
    }

    document.addEventListener('input', (e) => {
        if (e.target && e.target.classList.contains('part-master-col-filter')) {
            applyPartMasterHeaderFilters();
        }
    });

    document.getElementById('clearPartMasterFiltersBtn')?.addEventListener('click', () => {
        document.querySelectorAll('.part-master-col-filter').forEach(input => input.value = '');
        applyPartMasterHeaderFilters();
    });

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
            customer: document.getElementById('partCustomer').value,
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
            document.getElementById('partCustomer').value = p.customer || '';
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
                <select class="op-mach" style="width: 100%; padding: 8px;">
                    ${currentMachineOptions}
                </select>
            </td>
            <td><input type="number" step="0.01" class="op-time" value="${op.cycle_time || ''}" style="width: 100%; padding: 8px;"></td>
        `;
        const selectEl = tr.querySelector('.op-mach');
        if (op.machine) selectEl.value = op.machine;
        operationsBody.appendChild(tr);
        new TomSelect(selectEl, {
            create: true,
            sortField: { field: "text", direction: "asc" }
        });
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
                operatorsBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">No operators found.</td></tr>';
                return;
            }
            operators.forEach(o => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${o.id}</td><td>${o.department}</td><td>${o.name}</td><td>${o.designation || 'Operator'}</td>
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
        const data = {
            name: document.getElementById('operatorName').value,
            department: document.getElementById('operatorDepartment').value,
            designation: document.getElementById('operatorDesignation').value || 'Operator'
        };
        const url = id ? `/api/operators/${id}` : '/api/operators';
        await fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        closeOperatorModal(); fetchOperators();
    });

    window.deleteOperator = async (id) => {
        if (confirm('Delete this operator?')) {
            await fetch(`/api/operators/${id}`, { method: 'DELETE' });
            deburOperatorsLoaded = false;
            inspOperatorsLoaded = false;
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
            document.getElementById('operatorDesignation').value = o.designation || 'Operator';
            openOperatorModal(true);
        }
    };

    document.getElementById('deleteAllOperatorsBtn')?.addEventListener('click', async () => {
        if (confirm('Are you sure you want to delete ALL operator records? This cannot be undone.')) {
            try {
                const res = await fetch('/api/operators/all', { method: 'DELETE' });
                if (res.ok) {
                    alert('All operators deleted successfully.');
                    fetchOperators();
                } else {
                    alert('Failed to delete all operators.');
                }
            } catch (e) {
                console.error(e);
                alert('Error deleting all operators.');
            }
        }
    });

    // --- SETTERS LOGIC ---
    const settersBody = document.getElementById('settersBody');
    const setterModal = document.getElementById('setterModal');
    const setterForm = document.getElementById('setterForm');
    const closeSetterBtn = document.getElementById('closeSetterModalBtn');
    const cancelSetterBtn = document.getElementById('cancelSetterBtn');
    const setterModalTitle = document.getElementById('setterModalTitle');

    async function fetchSetters() {
        try {
            const response = await fetch('/api/setters');
            const setters = await response.json();
            if (settersBody) {
                settersBody.innerHTML = '';
                if (setters.length === 0) {
                    settersBody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">No setters found.</td></tr>';
                    return;
                }
                setters.forEach(s => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${s.id}</td><td>${s.department || ''}</td><td>${s.name}</td>
                        <td class="actions">
                            <button class="btn btn-edit" onclick="editSetter(${s.id})">Edit</button>
                            <button class="btn btn-danger" onclick="deleteSetter(${s.id})">Delete</button>
                        </td>`;
                    settersBody.appendChild(tr);
                });
            }
        } catch (e) { console.error(e); }
    }

    function openSetterModal(isEdit) {
        if (setterModal) {
            setterModal.classList.add('show');
            if (setterModalTitle) setterModalTitle.textContent = isEdit ? 'Edit Setter' : 'Add Setter';
        }
    }
    function closeSetterModal() {
        if (setterModal) setterModal.classList.remove('show');
        if (setterForm) setterForm.reset();
        const sId = document.getElementById('setterId');
        if (sId) sId.value = '';
    }
    if (closeSetterBtn) closeSetterBtn.addEventListener('click', closeSetterModal);
    if (cancelSetterBtn) cancelSetterBtn.addEventListener('click', closeSetterModal);

    if (setterForm) {
        setterForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('setterId').value;
            const data = {
                name: document.getElementById('setterName').value,
                department: document.getElementById('setterDepartment').value
            };
            const url = id ? `/api/setters/${id}` : '/api/setters';
            await fetch(url, {
                method: id ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            closeSetterModal();
            fetchSetters();
        });
    }

    window.deleteSetter = async (id) => {
        if (confirm('Delete this setter?')) {
            await fetch(`/api/setters/${id}`, { method: 'DELETE' });
            fetchSetters();
        }
    };

    window.editSetter = async (id) => {
        const res = await fetch('/api/setters');
        const data = await res.json();
        const s = data.find(x => x.id === id);
        if (s) {
            document.getElementById('setterId').value = s.id;
            document.getElementById('setterName').value = s.name;
            document.getElementById('setterDepartment').value = s.department || '';
            openSetterModal(true);
        }
    };

    // --- ATTENDANCE LOGIC ---
    const attendanceSection = document.getElementById('attendanceSection');
    const attendanceMonthPicker = document.getElementById('attendanceMonthPicker');
    const attendanceHead = document.getElementById('attendanceHead');
    const attendanceBody = document.getElementById('attendanceBody');

    async function initAttendance() {
        if (attendanceMonthPicker && !attendanceMonthPicker.value) {
            const now = new Date();
            const yyyy = now.getFullYear();
            const mm = String(now.getMonth() + 1).padStart(2, '0');
            attendanceMonthPicker.value = `${yyyy}-${mm}`;
        }
        await renderAttendanceGrid();
    }

    if (attendanceMonthPicker) {
        attendanceMonthPicker.addEventListener('change', () => {
            renderAttendanceGrid();
        });
    }

    async function renderAttendanceGrid() {
        if (!attendanceMonthPicker || !attendanceHead || !attendanceBody) return;
        const monthVal = attendanceMonthPicker.value;
        if (!monthVal) return;

        const parts = monthVal.split('-');
        const year = parseInt(parts[0]);
        const month = parseInt(parts[1]);
        const daysInMonth = new Date(year, month, 0).getDate();

        // Build Table Header with Sticky Positioning
        let trHead = '<tr style="background-color: #f1f5f9; font-weight: bold;">';
        trHead += '<th style="border: 1px solid #cbd5e1; padding: 6px; min-width: 140px; text-align: left; position: sticky; top: 0; background-color: #f1f5f9; z-index: 10;">Name</th>';
        trHead += '<th style="border: 1px solid #cbd5e1; padding: 6px; min-width: 80px; text-align: left; position: sticky; top: 0; background-color: #f1f5f9; z-index: 10;">Dept</th>';
        trHead += '<th style="border: 1px solid #cbd5e1; padding: 6px; min-width: 110px; text-align: left; position: sticky; top: 0; background-color: #f1f5f9; z-index: 10;">Designation</th>';

        for (let d = 1; d <= daysInMonth; d++) {
            const dateObj = new Date(year, month - 1, d);
            const isSunday = dateObj.getDay() === 0;
            if (isSunday) {
                trHead += `<th style="border: 1px solid #93c5fd; padding: 4px 2px; min-width: 36px; background-color: #dbeafe; color: #1e40af; font-weight: bold; position: sticky; top: 0; z-index: 10;">${d}<br><span style="font-size: 0.7rem; font-weight: normal;">Sun</span></th>`;
            } else {
                trHead += `<th style="border: 1px solid #cbd5e1; padding: 4px 2px; min-width: 36px; background-color: #f8fafc; position: sticky; top: 0; z-index: 10;">${d}</th>`;
            }
        }
        trHead += '</tr>';
        attendanceHead.innerHTML = trHead;

        // Fetch existing attendance for this month
        let existingRecords = [];
        try {
            const res = await fetch(`/api/attendance?month_year=${monthVal}`);
            existingRecords = await res.json();
        } catch (e) { console.error(e); }

        // Fetch operators to auto-populate employees if attendance is new
        let allOperators = [];
        try {
            const opRes = await fetch('/api/operators');
            allOperators = await opRes.json();
        } catch (e) { console.error(e); }

        // Group operators in exact sequence from Operator Master and map past hours
        const empMap = {};
        allOperators.forEach(op => {
            empMap[op.name] = {
                name: op.name,
                dept: op.department || '',
                designation: op.designation || 'Operator',
                days: {}
            };
        });

        existingRecords.forEach(r => {
            if (empMap[r.employee_name]) {
                empMap[r.employee_name].days[r.day] = r.hours;
            }
        });

        let empList = Object.values(empMap);

        attendanceBody.innerHTML = '';

        if (empList.length === 0) {
            for (let i = 0; i < 5; i++) {
                empList.push({ name: '', dept: '', designation: '', days: {} });
            }
        }

        empList.forEach(emp => {
            addAttendanceRow(emp, daysInMonth, year, month);
        });
    }

    function addAttendanceRow(emp = { name: '', dept: '', designation: '', days: {} }, daysInMonth = 31, year = 2026, month = 8) {
        if (!attendanceMonthPicker) return;
        const monthVal = attendanceMonthPicker.value;
        if (monthVal) {
            const parts = monthVal.split('-');
            year = parseInt(parts[0]);
            month = parseInt(parts[1]);
            daysInMonth = new Date(year, month, 0).getDate();
        }

        const tr = document.createElement('tr');
        tr.style.height = '32px';

        let rowHtml = `
            <td style="border: 1px solid #cbd5e1; padding: 2px;"><input type="text" class="att-name" value="${emp.name || ''}" placeholder="Name" style="width: 100%; border: none; font-size: 0.85rem; padding: 4px; background: transparent;"></td>
            <td style="border: 1px solid #cbd5e1; padding: 2px;"><input type="text" class="att-dept" value="${emp.dept || ''}" placeholder="Dept" style="width: 100%; border: none; font-size: 0.85rem; padding: 4px; background: transparent;"></td>
            <td style="border: 1px solid #cbd5e1; padding: 2px;"><input type="text" class="att-desig" value="${emp.designation || 'Operator'}" placeholder="Designation" style="width: 100%; border: none; font-size: 0.85rem; padding: 4px; background: transparent;"></td>
        `;

        for (let d = 1; d <= daysInMonth; d++) {
            const dateObj = new Date(year, month - 1, d);
            const isSunday = dateObj.getDay() === 0;
            const bgStyle = isSunday ? 'background-color: #eff6ff; border: 1px solid #bfdbfe;' : 'border: 1px solid #cbd5e1;';
            const val = emp.days && emp.days[d] !== undefined ? emp.days[d] : '';
            rowHtml += `
                <td style="${bgStyle} padding: 1px;">
                    <input type="text" class="att-day-val" data-day="${d}" value="${val}" style="width: 100%; text-align: center; border: none; background: transparent; font-size: 0.85rem; padding: 4px 1px;">
                </td>
            `;
        }

        tr.innerHTML = rowHtml;
        attendanceBody.appendChild(tr);
    }

    // Arrow Key Navigation for Attendance Grid
    attendanceBody?.addEventListener('keydown', (e) => {
        const input = e.target;
        if (!input || !input.tagName || input.tagName !== 'INPUT') return;

        const key = e.key;
        if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Enter'].includes(key)) return;

        const currentTd = input.closest('td');
        const currentTr = input.closest('tr');
        if (!currentTd || !currentTr) return;

        const cellIndex = currentTd.cellIndex;

        if (key === 'ArrowUp') {
            e.preventDefault();
            const prevTr = currentTr.previousElementSibling;
            if (prevTr) {
                const targetInput = prevTr.cells[cellIndex]?.querySelector('input');
                if (targetInput) { targetInput.focus(); targetInput.select(); }
            }
        } else if (key === 'ArrowDown' || key === 'Enter') {
            e.preventDefault();
            const nextTr = currentTr.nextElementSibling;
            if (nextTr) {
                const targetInput = nextTr.cells[cellIndex]?.querySelector('input');
                if (targetInput) { targetInput.focus(); targetInput.select(); }
            }
        } else if (key === 'ArrowLeft') {
            if (input.selectionStart === 0 && input.selectionEnd === 0) {
                e.preventDefault();
                const prevTd = currentTd.previousElementSibling;
                if (prevTd) {
                    const targetInput = prevTd.querySelector('input');
                    if (targetInput) { targetInput.focus(); targetInput.select(); }
                }
            }
        } else if (key === 'ArrowRight') {
            if (input.selectionStart === input.value.length && input.selectionEnd === input.value.length) {
                e.preventDefault();
                const nextTd = currentTd.nextElementSibling;
                if (nextTd) {
                    const targetInput = nextTd.querySelector('input');
                    if (targetInput) { targetInput.focus(); targetInput.select(); }
                }
            }
        }
    });

    document.getElementById('addAttendanceEmpBtn')?.addEventListener('click', () => {
        addAttendanceRow();
    });

    document.getElementById('saveAttendanceBtn')?.addEventListener('click', async () => {
        if (!attendanceMonthPicker) return;
        const monthVal = attendanceMonthPicker.value;
        if (!monthVal) {
            alert('Please select a Month/Year.');
            return;
        }

        const rows = attendanceBody.querySelectorAll('tr');
        const entries = [];

        rows.forEach(tr => {
            const name = tr.querySelector('.att-name')?.value.trim();
            const dept = tr.querySelector('.att-dept')?.value.trim();
            const desig = tr.querySelector('.att-desig')?.value.trim();

            if (name) {
                let hasHours = false;
                tr.querySelectorAll('.att-day-val').forEach(input => {
                    const day = parseInt(input.getAttribute('data-day'));
                    const hrs = input.value.trim();
                    if (hrs !== '') {
                        hasHours = true;
                        entries.push({
                            employee_name: name,
                            dept: dept || '',
                            designation: desig || 'Operator',
                            day: day,
                            hours: hrs
                        });
                    }
                });

                // Save employee details and designation even if no hours are entered yet
                if (!hasHours) {
                    entries.push({
                        employee_name: name,
                        dept: dept || '',
                        designation: desig || 'Operator',
                        day: 1,
                        hours: "0"
                    });
                }
            }
        });

        try {
            const res = await fetch('/api/attendance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    month_year: monthVal,
                    entries: entries
                })
            });
            if (res.ok) {
                alert(`Attendance for ${monthVal} saved successfully!`);
            } else {
                alert('Failed to save attendance.');
            }
        } catch (e) {
            console.error(e);
            alert('Error saving attendance.');
        }
    });

    document.getElementById('exportAttendanceExcelBtn')?.addEventListener('click', () => {
        const monthVal = attendanceMonthPicker ? attendanceMonthPicker.value : "Sheet";
        let daysInMonth = 31;
        if (monthVal) {
            const parts = monthVal.split('-');
            const year = parseInt(parts[0]);
            const month = parseInt(parts[1]);
            daysInMonth = new Date(year, month, 0).getDate();
        }

        // Build headers row
        const headers = ['NAME', 'DEPT', 'DESIGNATION'];
        for (let d = 1; d <= daysInMonth; d++) {
            headers.push(d.toString());
        }

        const data = [headers];

        // Build data rows from table inputs
        const rows = document.querySelectorAll('#attendanceBody tr');
        rows.forEach(tr => {
            const name = tr.querySelector('.att-name')?.value.trim() || '';
            const dept = tr.querySelector('.att-dept')?.value.trim() || '';
            const desig = tr.querySelector('.att-desig')?.value.trim() || '';

            if (name || dept) {
                const rowData = [name, dept, desig];
                const dayInputs = tr.querySelectorAll('.att-day-val');
                dayInputs.forEach(input => {
                    const val = input.value.trim();
                    const numVal = Number(val);
                    rowData.push(val !== '' && !isNaN(numVal) ? numVal : val);
                });
                data.push(rowData);
            }
        });

        if (data.length <= 1) {
            alert('No attendance data available to export.');
            return;
        }

        const ws = XLSX.utils.aoa_to_sheet(data);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Attendance");
        XLSX.writeFile(wb, `Attendance_${monthVal || 'Report'}.xlsx`);
    });

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
        const res = await fetch('/api/partmaster');
        allPartMasters = await res.json();
        // Force trigger change to populate datalist if dept is already selected
        scheduleDept.dispatchEvent(new Event('change'));
    }

    let schedulePartNoSelect = null;
    
    // Initialize TomSelect immediately
    const schedulePartNoEl = document.getElementById('schedulePartNo');
    if (schedulePartNoEl) {
        schedulePartNoSelect = new TomSelect(schedulePartNoEl, {
            create: false,
            sortField: { field: "text", direction: "asc" }
        });
    }
    
    scheduleDept.addEventListener('change', (e) => {
        const selectedDept = e.target.value;
        
        if (schedulePartNoSelect) {
            schedulePartNoSelect.clearOptions();
            schedulePartNoSelect.addOption({value: "", text: "Type or select a Part No"});
            if (selectedDept) {
                const selectedLower = selectedDept.trim().toLowerCase();
                const filteredParts = allPartMasters.filter(p => (p.department || '').trim().toLowerCase() === selectedLower);
                filteredParts.forEach(p => {
                    schedulePartNoSelect.addOption({value: p.partno, text: p.partno});
                });
            }
            schedulePartNoSelect.refreshOptions(false);
        }
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
                        <td>
                            <button onclick="editSchedule(${s.id})" style="background: none; border: none; color: var(--primary); cursor: pointer; margin-right: 8px;">Edit</button>
                            <button onclick="deleteSchedule(${s.id})" style="background: none; border: none; color: #ef4444; cursor: pointer;">Delete</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        } catch (e) {
            console.error('Error fetching schedules:', e);
        }
    }

    let editingScheduleId = null;

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
                const method = editingScheduleId ? 'PUT' : 'POST';
                const url = editingScheduleId ? `/api/schedule/${editingScheduleId}` : '/api/schedule';
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (response.ok) {
                    alert(editingScheduleId ? 'Schedule updated successfully!' : 'Schedule created successfully!');
                    const savedDate = document.getElementById('scheduleTargetDate').value;
                    scheduleCreateForm.reset();
                    if (savedDate) document.getElementById('scheduleTargetDate').value = savedDate;
                    editingScheduleId = null;
                    document.querySelector('#scheduleCreateForm button').textContent = 'Create Schedule';
                    scheduleDept.value = ''; // Reset dept field
                    if (schedulePartNoSelect) schedulePartNoSelect.clear();
                    scheduleDept.dispatchEvent(new Event('change'));
                    fetchSchedulesForList();
                } else {
                    alert('Error saving schedule.');
                }
            } catch (error) {
                console.error('Error:', error);
            }
        });
    }

    window.editSchedule = async function(id) {
        try {
            const res = await fetch('/api/schedule');
            const schedules = await res.json();
            const s = schedules.find(x => x.id === id);
            if (!s) return;
            
            editingScheduleId = id;
            
            document.getElementById('scheduleDept').value = s.department;
            scheduleDept.dispatchEvent(new Event('change'));
            
            setTimeout(() => {
                if (schedulePartNoSelect) schedulePartNoSelect.setValue(s.partno);
            }, 100);
            
            document.getElementById('scheduleTargetDate').value = s.target_date;
            document.getElementById('scheduleQty').value = s.qty;
            
            document.querySelector('#scheduleCreateForm button').textContent = 'Update Schedule';
        } catch (e) {
            console.error(e);
        }
    };

    window.deleteSchedule = async function(id) {
        if (!confirm('Are you sure you want to delete this schedule?')) return;
        try {
            const res = await fetch(`/api/schedule/${id}`, { method: 'DELETE' });
            if (res.ok) {
                fetchSchedulesForList();
            } else {
                alert('Failed to delete schedule.');
            }
        } catch (e) {
            console.error(e);
        }
    };

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
        loadSchedulePartNos();
        fetchSchedulesForList();
    });

    document.getElementById('exportRunBtn').addEventListener('click', () => {
        const table = document.getElementById('scheduleRunTable');
        if (!table) return;
        const wb = XLSX.utils.table_to_book(table, {sheet: "Schedule Run"});
        XLSX.writeFile(wb, `Schedule_Run_${new Date().toISOString().slice(0,10)}.xlsx`);
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
    let spiderStatusDataMap = {};
    
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
            const [schedRes, logRes, rmLogRes, htLogRes, htReceiptLogRes, rmRes] = await Promise.all([
                fetch('/api/schedule'),
                fetch('/api/prodlog'),
                fetch('/api/rawmateriallogs'),
                fetch('/api/ht_logs'),
                fetch('/api/ht_receipt_logs'),
                fetch('/api/rawmaterials')
            ]);
            
            const allSchedules = await schedRes.json();
            const allLogs = await logRes.json();
            const allRmLogs = await rmLogRes.json();
            const allHtLogs = await htLogRes.json();
            const allHtReceiptLogs = await htReceiptLogRes.json();
            const allRawMaterials = await rmRes.json();

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
                
                let opnBalances = [];
                const group1Parts = ["C100", "RS120", "RVI", "Q109", "R149", "RS160"];
                const isGroup1HT = group1Parts.includes((partno || '').trim().toUpperCase());

                // Opn 1 to 10
                for (let i = 0; i < 10; i++) {
                    if (i < operations.length) {
                        const currentOp = operations[i];
                        const nextOp = operations[i + 1];
                        
                        const opnClean = (currentOp.opn_no || '').trim().toLowerCase();
                        
                        // Total produced for current op from logs
                        let currentProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').trim().toLowerCase() === opnClean).reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                        
                        // Deduct HT sent for Turning (Opn 40 / OPN 3) for Group 1 HT parts
                        if (isGroup1HT && (opnClean === '40' || opnClean === 'opn 40' || opnClean === 'opn40')) {
                            const htSent = allHtLogs.filter(l => (l.partno || '').trim().toUpperCase() === (partno || '').trim().toUpperCase()).reduce((sum, l) => sum + (l.qty || 0), 0);
                            currentProd -= htSent;
                        }

                        // Set Opn 50 (HT Received / OPN 4 / For Grind) to HT Received total for Group 1 HT parts
                        if (isGroup1HT && (opnClean === '50' || opnClean === 'opn 50' || opnClean === 'opn50')) {
                            const htRec = allHtReceiptLogs.filter(l => (l.partno || '').trim().toUpperCase() === (partno || '').trim().toUpperCase()).reduce((sum, l) => sum + (l.qty || 0), 0);
                            currentProd = htRec;
                        }
                        
                        // Total produced for next op
                        let nextProd = 0;
                        if (nextOp) {
                            const nextOpClean = (nextOp.opn_no || '').trim().toLowerCase();
                            if (isGroup1HT && (nextOpClean === '50' || nextOpClean === 'opn 50' || nextOpClean === 'opn50')) {
                                nextProd = 0; // Opn 50 is HT Received, do not deduct from Opn 40 for Group 1
                            } else {
                                nextProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').trim().toLowerCase() === nextOpClean).reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                            }
                        } else {
                            const deburredTotal = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'debur').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                            const forInsLogTotal = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'for ins').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                            const rfdProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'rfd').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                            const reworkProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'rework').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                            const ncProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'nc').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                            const rejectionProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'rejection').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                            const totalInspected = Math.max(forInsLogTotal, rfdProd + reworkProd + ncProd + rejectionProd);
                            
                            nextProd = Math.max(deburredTotal, forInsLogTotal, totalInspected);
                        }
                        
                        let balance = currentProd - nextProd;
                        opnBalances.push(balance);
                        rowHtml += `<td>${balance}</td>`;
                    } else {
                        opnBalances.push(0);
                        rowHtml += `<td></td>`;
                    }
                }
                
                // fixed columns: debur, for ins, rework, nc, rfd, desp
                const deburredTotal = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'debur').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                const forInsLogTotal = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'for ins').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                const reworkProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'rework').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                const ncProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'nc').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                const rejectionProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'rejection').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                const rfdProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'rfd').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                const despProd = allRmLogs.filter(l => l.finish_part_no === partno && l.type === 'despatch').reduce((sum, l) => sum + (l.qty || 0), 0);

                const lastOpProd = operations.length > 0 ? allLogs.filter(l => l.partno === partno && (l.opn_no || '').trim().toLowerCase() === (operations[operations.length - 1].opn_no || '').trim().toLowerCase()).reduce((sum, l) => sum + (l.prod_qty || 0), 0) : 0;

                const effectiveForIns = deburredTotal > 0 ? deburredTotal : (forInsLogTotal > 0 ? forInsLogTotal : lastOpProd);
                const totalInspected = Math.max(forInsLogTotal, rfdProd + reworkProd + ncProd + rejectionProd);

                const deburBal = 0; // Deburring is completed once deburredTotal is logged
                const forInsBal = Math.max(0, effectiveForIns - totalInspected);
                const rfdBal = rfdProd - despProd;

                rowHtml += `<td>${deburBal}</td>`;
                rowHtml += `<td>${forInsBal}</td>`;
                rowHtml += `<td>${reworkProd}</td>`;
                rowHtml += `<td>${ncProd}</td>`;
                rowHtml += `<td>${rfdBal}</td>`;
                rowHtml += `<td>${despProd}</td>`;
                
                spiderStatusDataMap[(partno || '').trim().toUpperCase()] = {
                    schedQty,
                    opnBalances,
                    forInsBal,
                    rfdBal,
                    despProd
                };
                
                const tr = document.createElement('tr');
                tr.innerHTML = rowHtml;
                tbody.appendChild(tr);
            }

            if (dept.trim().toUpperCase() === 'SPIDER') {
                await renderSpiderReport(allSchedules, allLogs, allRmLogs, allHtLogs, allHtReceiptLogs, allRawMaterials);
            } else {
                const spiderContainer = document.getElementById('spiderReportContainer');
                if (spiderContainer) spiderContainer.style.display = 'none';
            }
        } catch (e) {
            console.error('Error fetching schedule status:', e);
        }
    }

    async function renderSpiderReport(allSchedules, allLogs, allRmLogs, allHtLogs, allHtReceiptLogs, allRawMaterials = null) {
        const spiderContainer = document.getElementById('spiderReportContainer');
        const tbody = document.getElementById('spiderReportBody');
        if (!spiderContainer || !tbody) return;

        spiderContainer.style.display = 'block';
        tbody.innerHTML = '';

        let allRms = allRawMaterials;
        if (!allRms) {
            try {
                const rRes = await fetch('/api/rawmaterials');
                allRms = await rRes.json();
            } catch(e) { allRms = []; }
        }

        const groups = [
            {
                name: "Group 1",
                parts: ["C100", "RS120", "RVI", "Q109", "R149", "RS160"],
                headers: [
                    { title: "Part No", rowspan: 2 },
                    { title: "sch qty", rowspan: 2 },
                    { title: "F Avail", rowspan: 2 },
                    { title: "WIP", rowspan: 2 },
                    { title: "RM Status", rowspan: 2 },
                    { title: "Fac & cen", rowspan: 2 },
                    { title: "HT", colspan: 3, subList: ["For HT", "Anusha", "JMS"] },
                    { title: "Grinding", colspan: 2, subList: ["For Grind", "For Ins"] },
                    { title: "RFD", rowspan: 2 },
                    { title: "Despatch", rowspan: 2 }
                ]
            },
            {
                name: "Group 2",
                parts: ["QD", "AMW", "15 I"],
                headers: [
                    { title: "Part No" },
                    { title: "sch qty" },
                    { title: "F Avail" },
                    { title: "WIP" },
                    { title: "RM Status" },
                    { title: "Boring" },
                    { title: "Fac & cen" },
                    { title: "turning" },
                    { title: "drilling" },
                    { title: "Inspec" },
                    { title: "RFD" },
                    { title: "Despatch" }
                ]
            },
            {
                name: "Group 3",
                parts: ["HR Forward"],
                headers: [
                    { title: "Part No" },
                    { title: "sch qty" },
                    { title: "F Avail" },
                    { title: "WIP" },
                    { title: "RM Status" },
                    { title: "Boring" },
                    { title: "Fac & cen" },
                    { title: "Pre Turn" },
                    { title: "Spherical" },
                    { title: "Inspec" },
                    { title: "RFD" },
                    { title: "Despatch" }
                ]
            },
            {
                name: "Group 4",
                parts: ["HR Rear"],
                headers: [
                    { title: "Part No" },
                    { title: "sch qty" },
                    { title: "F Avail" },
                    { title: "WIP" },
                    { title: "RM Status" },
                    { title: "Boring" },
                    { title: "Thickness" },
                    { title: "Fac & cen" },
                    { title: "Turning" },
                    { title: "Inspec" },
                    { title: "RFD" },
                    { title: "Despatch" }
                ]
            }
        ];

        for (const group of groups) {
            const trHeader1 = document.createElement('tr');
            trHeader1.style.backgroundColor = '#dbeafe';
            trHeader1.style.fontWeight = 'bold';
            
            const trHeader2 = document.createElement('tr');
            trHeader2.style.backgroundColor = '#eff6ff';
            trHeader2.style.fontWeight = 'bold';

            group.headers.forEach(h => {
                if (h.rowspan === 2) {
                    trHeader1.innerHTML += `<th rowspan="2" style="border:1px solid #cbd5e1; padding:6px; text-align:center; background:#dbeafe;">${h.title}</th>`;
                } else if (h.colspan) {
                    trHeader1.innerHTML += `<th colspan="${h.colspan}" style="border:1px solid #cbd5e1; padding:6px; text-align:center; background:#dbeafe;">${h.title}</th>`;
                    if (h.subList) {
                        h.subList.forEach(sub => {
                            trHeader2.innerHTML += `<th style="border:1px solid #cbd5e1; padding:6px; text-align:center; background:#eff6ff;">${sub}</th>`;
                        });
                    }
                } else {
                    trHeader1.innerHTML += `<th style="border:1px solid #cbd5e1; padding:6px; text-align:center; background:#dbeafe;">${h.title}</th>`;
                    if (h.sub) {
                        trHeader2.innerHTML += `<th style="border:1px solid #cbd5e1; padding:6px; text-align:center; background:#eff6ff;">${h.sub}</th>`;
                    }
                }
            });

            tbody.appendChild(trHeader1);
            if (trHeader2.children.length > 0) {
                tbody.appendChild(trHeader2);
            }

            for (const pName of group.parts) {
                const partKey = pName.trim().toUpperCase();
                const partObj = statusAllParts.find(p => (p.partno || '').trim().toUpperCase() === partKey);
                const sData = spiderStatusDataMap[partKey] || { schedQty: 0, opnBalances: [0,0,0,0,0,0,0,0,0,0], rfdBal: 0, despProd: 0 };
                const opn = sData.opnBalances || [0,0,0,0,0,0,0,0,0,0];

                const fpn = partObj ? (partObj.forge_pn || '').trim().toUpperCase() : '';
                
                // Match RM stock by partno or by forge_pn
                const rmObj = (allRms || []).find(r => {
                    const rKey = (r.forge_pn || '').trim().toUpperCase();
                    return rKey === partKey || (fpn && rKey === fpn);
                });
                
                let fAvail = 0;
                if (rmObj) {
                    fAvail = (rmObj.stock !== undefined && rmObj.stock !== null) ? parseInt(rmObj.stock) : ((parseInt(rmObj.receipt) || 0) - (parseInt(rmObj.despatch) || 0));
                    if (isNaN(fAvail)) fAvail = 0;
                }

                const sentAnusha = allHtLogs.filter(l => (l.partno || '').trim().toUpperCase() === partKey && (l.vendor || '').toLowerCase().includes('anusha')).reduce((sum, l) => sum + (l.qty || 0), 0);
                const recAnusha = allHtReceiptLogs.filter(l => (l.partno || '').trim().toUpperCase() === partKey && (l.vendor || '').toLowerCase().includes('anusha')).reduce((sum, l) => sum + (l.qty || 0), 0);
                const pendingAnusha = Math.max(0, sentAnusha - recAnusha);

                const sentJMS = allHtLogs.filter(l => (l.partno || '').trim().toUpperCase() === partKey && (l.vendor || '').toLowerCase().includes('jms')).reduce((sum, l) => sum + (l.qty || 0), 0);
                const recJMS = allHtReceiptLogs.filter(l => (l.partno || '').trim().toUpperCase() === partKey && (l.vendor || '').toLowerCase().includes('jms')).reduce((sum, l) => sum + (l.qty || 0), 0);
                const pendingJMS = Math.max(0, sentJMS - recJMS);

                const trRow = document.createElement('tr');
                let rowContent = `<td style="border:1px solid #cbd5e1; padding:6px; font-weight:bold;">${pName}</td>`;
                rowContent += `<td style="border:1px solid #cbd5e1; padding:6px;">${sData.schedQty || 0}</td>`;
                rowContent += `<td style="border:1px solid #cbd5e1; padding:6px;">${fAvail || 0}</td>`;

                if (group.name === 'Group 1') {
                    const facCen = opn[1] || 0;
                    const forHt = opn[2] || 0;
                    const forGrind = opn[3] || 0;
                    const forIns = opn[4] || 0;
                    const rfdVal = sData.rfdBal || 0;

                    const wip = facCen + forHt + pendingAnusha + pendingJMS + forGrind + forIns + rfdVal;
                    const rmStatus = fAvail - wip;

                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px; font-weight:600;">${wip}</td>`;
                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px; font-weight:600; color: ${rmStatus < 0 ? '#ef4444' : '#16a34a'};">${rmStatus}</td>`;
                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px;">${facCen}</td>`;
                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px;">${forHt}</td>`;
                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px; color:#d97706; font-weight:bold;">${pendingAnusha}</td>`;
                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px; color:#d97706; font-weight:bold;">${pendingJMS}</td>`;
                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px;">${forGrind}</td>`;
                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px;">${forIns}</td>`;
                } else if (group.name === 'Group 2' || group.name === 'Group 3' || group.name === 'Group 4') {
                    const opn0 = opn[0] || 0;
                    const opn1 = opn[1] || 0;
                    const opn2 = opn[2] || 0;
                    const opn3 = opn[3] || 0;
                    const forInsBal = sData.forInsBal || 0;
                    const rfdVal = sData.rfdBal || 0;

                    const wip = opn0 + opn1 + opn2 + opn3 + forInsBal + rfdVal;
                    const rmStatus = fAvail - wip;

                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px; font-weight:600;">${wip}</td>`;
                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px; font-weight:600; color: ${rmStatus < 0 ? '#ef4444' : '#16a34a'};">${rmStatus}</td>`;
                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px;">${opn0}</td>`;
                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px;">${opn1}</td>`;
                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px;">${opn2}</td>`;
                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px;">${opn3}</td>`;
                    rowContent += `<td style="border:1px solid #cbd5e1; padding:6px;">${forInsBal}</td>`;
                }

                rowContent += `<td style="border:1px solid #cbd5e1; padding:6px;">${sData.rfdBal || 0}</td>`;
                rowContent += `<td style="border:1px solid #cbd5e1; padding:6px;">${sData.despProd || 0}</td>`;

                trRow.innerHTML = rowContent;
                tbody.appendChild(trRow);
            }
        }
    }

    const exportSpiderBtn = document.getElementById('exportSpiderReportBtn');
    if (exportSpiderBtn) {
        exportSpiderBtn.addEventListener('click', () => {
            const table = document.getElementById('spiderReportTable');
            if (!table) return;
            const wb = XLSX.utils.table_to_book(table, {sheet: "SPIDER Report"});
            XLSX.writeFile(wb, `SPIDER_Detailed_Report_${new Date().toISOString().slice(0,10)}.xlsx`);
        });
    }

    // --- DEBUR LOGIC ---
    let deburAllParts = [];
    let deburOperatorsLoaded = false;
    
    document.getElementById('deburDeptSelect').addEventListener('change', fetchDeburStatus);
    
    async function initDebur() {
        try {
            if (!document.getElementById('deburDate').value) {
                document.getElementById('deburDate').valueAsDate = new Date();
            }
            
            if (deburAllParts.length === 0) {
                const partsRes = await fetch('/api/partmaster');
                deburAllParts = await partsRes.json();
            }
            if (!deburOperatorsLoaded) {
                const opRes = await fetch('/api/operators');
                const operators = await opRes.json();
                operators.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
                const sel = document.getElementById('deburOperator');
                if (sel) {
                    sel.innerHTML = '<option value="">-- Select Operator --</option>';
                    operators.forEach(o => {
                        const opt = document.createElement('option');
                        opt.value = o.name;
                        opt.textContent = o.name;
                        sel.appendChild(opt);
                    });
                }
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
            cycle_time: 0,
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
    let savedInspectionReasons = new Set();

    document.getElementById('inspDeptSelect').addEventListener('change', fetchInspectionStatus);

    async function loadPastInspectionReasons() {
        try {
            const res = await fetch('/api/prodlog');
            const logs = await res.json();
            logs.forEach(l => {
                const op = (l.opn_no || '').toLowerCase();
                if (['rejection', 'rework', 'nc'].includes(op)) {
                    const rsn = (l.idle_reason || l.description || '').trim();
                    if (rsn && rsn !== 'None' && rsn !== 'Rejection' && rsn !== 'Rework' && rsn !== 'NC') {
                        savedInspectionReasons.add(rsn);
                    }
                }
            });
            updateReasonsDatalist();
        } catch (e) { console.error(e); }
    }

    function updateReasonsDatalist() {
        const datalist = document.getElementById('inspectionReasonsDatalist');
        if (!datalist) return;
        datalist.innerHTML = '';
        savedInspectionReasons.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r;
            datalist.appendChild(opt);
        });
    }

    function createInspectionRow(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const rowDiv = document.createElement('div');
        rowDiv.className = 'insp-detail-row';
        rowDiv.style.display = 'flex';
        rowDiv.style.gap = '8px';
        rowDiv.style.alignItems = 'center';

        rowDiv.innerHTML = `
            <input type="number" class="insp-row-qty" placeholder="Qty" min="1" style="width: 100px; padding: 0.4rem 0.6rem; border-radius: 8px; border: 1px solid var(--border-color); background: rgba(0,0,0,0.05); color: var(--text-main); font-family: 'Inter', sans-serif;">
            <input type="text" class="insp-row-reason" list="inspectionReasonsDatalist" placeholder="Type or select reason..." style="flex: 1; padding: 0.4rem 0.6rem; border-radius: 8px; border: 1px solid var(--border-color); background: rgba(0,0,0,0.05); color: var(--text-main); font-family: 'Inter', sans-serif;">
            <button type="button" class="btn-text remove-insp-row-btn" style="color: #ef4444; font-size: 1.2rem; font-weight: bold; cursor: pointer; padding: 0 6px;">&times;</button>
        `;

        rowDiv.querySelector('.remove-insp-row-btn').addEventListener('click', () => {
            rowDiv.remove();
            autoSumInspection();
        });

        rowDiv.querySelector('.insp-row-qty').addEventListener('input', autoSumInspection);

        container.appendChild(rowDiv);
    }

    function initInspectionRows() {
        ['rejectionRowsContainer', 'reworkRowsContainer', 'ncRowsContainer'].forEach(cId => {
            const container = document.getElementById(cId);
            if (container && container.children.length === 0) {
                createInspectionRow(cId);
            }
        });
    }

    document.getElementById('addRejectionRowBtn')?.addEventListener('click', () => createInspectionRow('rejectionRowsContainer'));
    document.getElementById('addReworkRowBtn')?.addEventListener('click', () => createInspectionRow('reworkRowsContainer'));
    document.getElementById('addNCRowBtn')?.addEventListener('click', () => createInspectionRow('ncRowsContainer'));

    async function initInspection() {
        try {
            if (!document.getElementById('inspDate').value) {
                document.getElementById('inspDate').valueAsDate = new Date();
            }
            
            if (inspAllParts.length === 0) {
                const partsRes = await fetch('/api/partmaster');
                inspAllParts = await partsRes.json();
            }
            if (!inspOperatorsLoaded) {
                const opRes = await fetch('/api/operators');
                const operators = await opRes.json();
                operators.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
                const sel = document.getElementById('inspOperator');
                if (sel) {
                    sel.innerHTML = '<option value="">-- Select Operator --</option>';
                    operators.forEach(o => {
                        const opt = document.createElement('option');
                        opt.value = o.name;
                        opt.textContent = o.name;
                        sel.appendChild(opt);
                    });
                }
                inspOperatorsLoaded = true;
            }
            
            loadPastInspectionReasons();
            initInspectionRows();
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
            const [schedRes, logRes, pmRes] = await Promise.all([
                fetch('/api/schedule'),
                fetch('/api/prodlog'),
                fetch('/api/partmaster')
            ]);
            
            const allSchedules = await schedRes.json();
            const allLogs = await logRes.json();
            const allPartMasters = await pmRes.json();
            
            const deptSchedules = allSchedules.filter(s => (s.department || '').trim().toUpperCase() === dept.trim().toUpperCase() && (s.status === 'Pending' || !s.status));
            const uniqueParts = [...new Set(deptSchedules.map(s => s.partno))];
            
            if (uniqueParts.length === 0) {
                tbody.innerHTML = '<tr><td colspan="2" style="color:var(--text-muted); text-align:center;">No pending parts for this department</td></tr>';
                return;
            }
            
            for (const partno of uniqueParts) {
                const partObj = allPartMasters.find(p => (p.partno || '').trim().toUpperCase() === (partno || '').trim().toUpperCase());
                let lastOpnNo = '';
                if (partObj) {
                    const opsRes = await fetch(`/api/partmaster/${partObj.id}/operations`);
                    const operations = await opsRes.json();
                    if (operations.length > 0) {
                        operations.sort((a, b) => (parseInt(a.opn_no) || 0) - (parseInt(b.opn_no) || 0));
                        lastOpnNo = (operations[operations.length - 1].opn_no || '').trim().toLowerCase();
                    }
                }

                const deburredTotal = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'debur').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                const forInsLogTotal = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'for ins').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                const lastOpProd = lastOpnNo ? allLogs.filter(l => l.partno === partno && (l.opn_no || '').trim().toLowerCase() === lastOpnNo).reduce((sum, l) => sum + (l.prod_qty || 0), 0) : 0;

                const effectiveForIns = deburredTotal > 0 ? deburredTotal : (forInsLogTotal > 0 ? forInsLogTotal : lastOpProd);

                const rfdProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'rfd').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                const reworkProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'rework').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                const ncProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'nc').reduce((sum, l) => sum + (l.prod_qty || 0), 0);
                const rejectionProd = allLogs.filter(l => l.partno === partno && (l.opn_no || '').toLowerCase() === 'rejection').reduce((sum, l) => sum + (l.prod_qty || 0), 0);

                const totalInspected = Math.max(forInsLogTotal, rfdProd + reworkProd + ncProd + rejectionProd);

                const balance = Math.max(0, effectiveForIns - totalInspected);
                
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
    
    function autoSumInspection() {
        const rfd = parseInt(document.getElementById('inspRFD').value) || 0;
        
        let totalRej = 0;
        document.querySelectorAll('#rejectionRowsContainer .insp-row-qty').forEach(input => {
            totalRej += parseInt(input.value) || 0;
        });

        let totalRew = 0;
        document.querySelectorAll('#reworkRowsContainer .insp-row-qty').forEach(input => {
            totalRew += parseInt(input.value) || 0;
        });

        let totalNC = 0;
        document.querySelectorAll('#ncRowsContainer .insp-row-qty').forEach(input => {
            totalNC += parseInt(input.value) || 0;
        });

        const sum = rfd + totalRej + totalRew + totalNC;
        if (sum > 0) {
            document.getElementById('inspQty').value = sum;
        }
    }
    document.getElementById('inspRFD')?.addEventListener('input', autoSumInspection);

    document.getElementById('inspForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const date = document.getElementById('inspDate').value;
        const operator = document.getElementById('inspOperator').value;
        const partno = document.getElementById('inspPartNo').value;
        const runtime = parseFloat(document.getElementById('inspHours').value) || 0;
        const dept = document.getElementById('inspDeptSelect').value;
        
        const inspQty = parseInt(document.getElementById('inspQty').value) || 0;
        const rfdQty = parseInt(document.getElementById('inspRFD').value) || 0;
        
        if (inspQty === 0) {
            alert("Total Inspected quantity cannot be zero.");
            return;
        }
        
        const createPayload = (opn_no, qty, reason = '') => ({
            dept, date, shift: '', setter: '', machine: '',
            operator, partno, opn_no, description: reason, runtime,
            cycle_time: 0, target_qty: 0, prod_qty: qty, efficiency: 0,
            idle_hours: 0, idle_reason: reason
        });
        
        const payloads = [];
        payloads.push(createPayload('for ins', inspQty));
        if (rfdQty > 0) payloads.push(createPayload('rfd', rfdQty));

        // Rejection rows
        document.querySelectorAll('#rejectionRowsContainer .insp-detail-row').forEach(row => {
            const qty = parseInt(row.querySelector('.insp-row-qty').value) || 0;
            const rsn = row.querySelector('.insp-row-reason').value.trim();
            if (qty > 0) {
                payloads.push(createPayload('rejection', qty, rsn || 'Rejection'));
                if (rsn) savedInspectionReasons.add(rsn);
            }
        });

        // Rework rows
        document.querySelectorAll('#reworkRowsContainer .insp-detail-row').forEach(row => {
            const qty = parseInt(row.querySelector('.insp-row-qty').value) || 0;
            const rsn = row.querySelector('.insp-row-reason').value.trim();
            if (qty > 0) {
                payloads.push(createPayload('rework', qty, rsn || 'Rework'));
                if (rsn) savedInspectionReasons.add(rsn);
            }
        });

        // NC rows
        document.querySelectorAll('#ncRowsContainer .insp-detail-row').forEach(row => {
            const qty = parseInt(row.querySelector('.insp-row-qty').value) || 0;
            const rsn = row.querySelector('.insp-row-reason').value.trim();
            if (qty > 0) {
                payloads.push(createPayload('nc', qty, rsn || 'NC'));
                if (rsn) savedInspectionReasons.add(rsn);
            }
        });
        
        updateReasonsDatalist();

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
                document.getElementById('inspRFD').value = '';
                
                ['rejectionRowsContainer', 'reworkRowsContainer', 'ncRowsContainer'].forEach(cId => {
                    const c = document.getElementById(cId);
                    if (c) c.innerHTML = '';
                });
                initInspectionRows();
                
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

    let currentInspExportData = [];

    async function fetchInspectionLogs() {
        try {
            const res = await fetch('/api/prodlog');
            const allLogs = await res.json();
            const inspLogs = allLogs.filter(l => (l.opn_no || '').toLowerCase() === 'for ins');
            
            inspLogs.sort((a, b) => b.id - a.id);
            
            const tbody = document.getElementById('inspLogsBody');
            tbody.innerHTML = '';
            
            if (inspLogs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--text-muted)">No inspection logs found.</td></tr>';
                currentInspExportData = [];
                return;
            }
            
            currentInspExportData = [];

            inspLogs.slice(0, 50).forEach(log => {
                const date = log.date;
                const op = log.operator || '';
                const pno = log.partno;
                
                const rfdLogs = allLogs.filter(l => l.partno === pno && l.date === date && l.operator === op && (l.opn_no || '').toLowerCase() === 'rfd' && Math.abs((l.id || 0) - (log.id || 0)) <= 15);
                const rejLogs = allLogs.filter(l => l.partno === pno && l.date === date && l.operator === op && (l.opn_no || '').toLowerCase() === 'rejection' && Math.abs((l.id || 0) - (log.id || 0)) <= 15);
                const rewLogs = allLogs.filter(l => l.partno === pno && l.date === date && l.operator === op && (l.opn_no || '').toLowerCase() === 'rework' && Math.abs((l.id || 0) - (log.id || 0)) <= 15);
                const ncLogs = allLogs.filter(l => l.partno === pno && l.date === date && l.operator === op && (l.opn_no || '').toLowerCase() === 'nc' && Math.abs((l.id || 0) - (log.id || 0)) <= 15);

                const totalRfd = rfdLogs.reduce((s, l) => s + (l.prod_qty || 0), 0);

                const rejText = rejLogs.map(l => `${l.prod_qty} (${l.idle_reason || l.description || ''})`).join(', ') || '0';
                const rewText = rewLogs.map(l => `${l.prod_qty} (${l.idle_reason || l.description || ''})`).join(', ') || '0';
                const ncText = ncLogs.map(l => `${l.prod_qty} (${l.idle_reason || l.description || ''})`).join(', ') || '0';

                currentInspExportData.push({
                    "Date": date,
                    "Operator": op,
                    "Part No": pno,
                    "Hours": log.runtime || 0,
                    "Total Inspected": log.prod_qty || 0,
                    "RFD": totalRfd,
                    "Rejection": rejText,
                    "Rework": rewText,
                    "NC": ncText
                });

                const rejStr = rejLogs.map(l => `<span style="color:#ef4444; font-weight:600;">${l.prod_qty}</span> <small style="color:var(--text-muted);">(${l.idle_reason || l.description || ''})</small>`).join('<br>') || '0';
                const rewStr = rewLogs.map(l => `<span style="color:#f59e0b; font-weight:600;">${l.prod_qty}</span> <small style="color:var(--text-muted);">(${l.idle_reason || l.description || ''})</small>`).join('<br>') || '0';
                const ncStr = ncLogs.map(l => `<span style="color:#6366f1; font-weight:600;">${l.prod_qty}</span> <small style="color:var(--text-muted);">(${l.idle_reason || l.description || ''})</small>`).join('<br>') || '0';

                const allRelatedIds = [log.id, ...rfdLogs.map(l => l.id), ...rejLogs.map(l => l.id), ...rewLogs.map(l => l.id), ...ncLogs.map(l => l.id)];

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${log.date}</td>
                    <td>${log.operator || ''}</td>
                    <td>${log.partno}</td>
                    <td>${log.runtime || ''}</td>
                    <td><span style="font-weight: bold; color: var(--primary-color);">${log.prod_qty || 0}</span></td>
                    <td><span style="color:#10b981; font-weight:600;">${totalRfd}</span></td>
                    <td>${rejStr}</td>
                    <td>${rewStr}</td>
                    <td>${ncStr}</td>
                    <td>
                        <button class="delete-insp-log-btn btn-text" style="color: #ef4444; cursor: pointer; padding: 2px 6px; font-size: 0.85rem;" title="Delete Log">
                            <i class="fas fa-trash-alt"></i> Delete
                        </button>
                    </td>
                `;

                tr.querySelector('.delete-insp-log-btn').addEventListener('click', async () => {
                    if (confirm(`Are you sure you want to delete inspection log for Part No: ${pno} (Date: ${date})?`)) {
                        try {
                            for (const id of allRelatedIds) {
                                await fetch(`/api/prodlog/${id}`, { method: 'DELETE' });
                            }
                            fetchInspectionStatus();
                            fetchInspectionLogs();
                        } catch (err) {
                            console.error('Error deleting inspection log:', err);
                            alert("Failed to delete log.");
                        }
                    }
                });

                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error('Error fetching inspection logs:', e);
        }
    }

    document.getElementById('exportInspLogsBtn')?.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/prodlog');
            const allLogs = await res.json();
            const inspLogs = allLogs.filter(l => (l.opn_no || '').toLowerCase() === 'for ins');
            
            inspLogs.sort((a, b) => b.id - a.id);
            
            if (inspLogs.length === 0) {
                alert("No inspection logs available to export.");
                return;
            }

            const exportRows = [];

            inspLogs.forEach(log => {
                const date = log.date;
                const op = log.operator || '';
                const pno = log.partno;

                const rfdLogs = allLogs.filter(l => l.partno === pno && l.date === date && l.operator === op && (l.opn_no || '').toLowerCase() === 'rfd' && Math.abs((l.id || 0) - (log.id || 0)) <= 15);
                const rejLogs = allLogs.filter(l => l.partno === pno && l.date === date && l.operator === op && (l.opn_no || '').toLowerCase() === 'rejection' && Math.abs((l.id || 0) - (log.id || 0)) <= 15);
                const rewLogs = allLogs.filter(l => l.partno === pno && l.date === date && l.operator === op && (l.opn_no || '').toLowerCase() === 'rework' && Math.abs((l.id || 0) - (log.id || 0)) <= 15);
                const ncLogs = allLogs.filter(l => l.partno === pno && l.date === date && l.operator === op && (l.opn_no || '').toLowerCase() === 'nc' && Math.abs((l.id || 0) - (log.id || 0)) <= 15);

                const totalRfd = rfdLogs.reduce((s, l) => s + (l.prod_qty || 0), 0);
                const maxRows = Math.max(1, rejLogs.length, rewLogs.length, ncLogs.length);

                for (let i = 0; i < maxRows; i++) {
                    exportRows.push({
                        "Date": i === 0 ? date : '',
                        "Operator": i === 0 ? op : '',
                        "Part No": i === 0 ? pno : '',
                        "Hours": i === 0 ? (log.runtime || 0) : '',
                        "Total Inspected": i === 0 ? (log.prod_qty || 0) : '',
                        "RFD": i === 0 ? totalRfd : '',
                        "Rejection Qty": rejLogs[i] ? rejLogs[i].prod_qty : '',
                        "Rejection Reason": rejLogs[i] ? (rejLogs[i].idle_reason || rejLogs[i].description || '') : '',
                        "Rework Qty": rewLogs[i] ? rewLogs[i].prod_qty : '',
                        "Rework Reason": rewLogs[i] ? (rewLogs[i].idle_reason || rewLogs[i].description || '') : '',
                        "NC Qty": ncLogs[i] ? ncLogs[i].prod_qty : '',
                        "NC Reason": ncLogs[i] ? (ncLogs[i].idle_reason || ncLogs[i].description || '') : ''
                    });
                }
            });

            const ws = XLSX.utils.json_to_sheet(exportRows);
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, "Inspection Logs");
            XLSX.writeFile(wb, `Inspection_Logs_${new Date().toISOString().slice(0, 10)}.xlsx`);
        } catch (err) {
            console.error("Error exporting inspection logs:", err);
            alert("Failed to export inspection logs.");
        }
    });

    // --- PROD LOG LOGIC ---
    let prodLogAllMachines = [];
    let prodLogAllOperators = [];
    let prodLogAllSetters = [];
    let prodLogSchedules = [];
    let currentPartOperations = [];

    async function initProdLog() {
        if (!document.getElementById('prodLogDate').value) {
            document.getElementById('prodLogDate').valueAsDate = new Date();
        }
        
        // Fetch dependencies
        const machRes = await fetch('/api/machines');
        prodLogAllMachines = await machRes.json();
        
        const opRes = await fetch('/api/operators');
        prodLogAllOperators = await opRes.json();

        const setterRes = await fetch('/api/setters');
        prodLogAllSetters = await setterRes.json();

        // Populate Setter dropdown
        const setterSelect = document.getElementById('prodLogSetter');
        if (setterSelect) {
            setterSelect.innerHTML = '<option value="">-- Select Setter --</option>';
            prodLogAllSetters.forEach(s => {
                setterSelect.innerHTML += `<option value="${s.name}">${s.name}</option>`;
            });
        }
        
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
        const setterSelect = document.getElementById('prodLogSetter');
        const partList = document.getElementById('prodLogPartNoList');
        
        machSelect.innerHTML = '<option value="">-- Select Machine --</option>';
        opSelect.innerHTML = '<option value="">-- Select Operator --</option>';
        if (setterSelect) setterSelect.innerHTML = '<option value="">-- Select Setter --</option>';
        document.getElementById('prodLogPartNo').value = '';
        partList.innerHTML = '';
        
        prodLogAllMachines.filter(m => (m.department || '').trim().toUpperCase() === dept).forEach(m => {
            machSelect.innerHTML += `<option value="${m.name}">${m.name}</option>`;
        });
        
        const filteredOperators = prodLogAllOperators.filter(o => !dept || !o.department || (o.department || '').trim().toUpperCase() === dept);
        const opsToDisplay = filteredOperators.length > 0 ? filteredOperators : prodLogAllOperators;
        opsToDisplay.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        opsToDisplay.forEach(o => {
            opSelect.innerHTML += `<option value="${o.name}">${o.name}</option>`;
        });

        if (setterSelect) {
            const filteredSetters = prodLogAllSetters.filter(s => !dept || !s.department || s.department.trim().toUpperCase() === dept);
            const settersToDisplay = filteredSetters.length > 0 ? filteredSetters : prodLogAllSetters;
            settersToDisplay.forEach(s => {
                setterSelect.innerHTML += `<option value="${s.name}">${s.name}</option>`;
            });
        }
        
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

    function validateHours() {
        const shiftName = document.getElementById('prodLogShift').value;
        const shiftObj = allShifts.find(s => s.name === shiftName);
        const maxHours = shiftObj ? parseFloat(shiftObj.hours || 0) : 0;
        
        const warningEl = document.getElementById('prodLogHoursWarning');
        if (!warningEl) return;
        
        if (maxHours === 0) {
            warningEl.style.display = 'none';
            return;
        }

        const runtime = parseFloat(document.getElementById('prodLogRuntime').value) || 0;
        const idle1 = parseFloat(document.getElementById('prodLogIdleHours').value) || 0;
        const idle2 = parseFloat(document.getElementById('prodLogIdleHours2').value) || 0;
        const idle3 = parseFloat(document.getElementById('prodLogIdleHours3').value) || 0;
        const totalCurrent = runtime + idle1 + idle2 + idle3;
        
        const continueOp = document.getElementById('prodLogContinueOperator') ? document.getElementById('prodLogContinueOperator').value : 'n';
        
        let totalToValidate = totalCurrent;
        if (continueOp === 'y') {
            totalToValidate += currentOperatorSessionHours;
        }
        
        if (totalToValidate > maxHours) {
            warningEl.innerText = `Run time & Idle time more than log hours (${maxHours})`;
            warningEl.style.display = 'block';
        } else {
            warningEl.style.display = 'none';
        }
    }

    ['prodLogShift', 'prodLogRuntime', 'prodLogIdleHours', 'prodLogIdleHours2', 'prodLogIdleHours3'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', validateHours);
    });
    const continueOpEl = document.getElementById('prodLogContinueOperator');
    if (continueOpEl) continueOpEl.addEventListener('change', validateHours);

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
                    <td>${log.date ? log.date.split('-').reverse().join('/') : ''}</td>
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
                actionTd.style.whiteSpace = 'nowrap';

                const editBtn = document.createElement('button');
                editBtn.className = 'btn-text';
                editBtn.style.color = 'var(--primary-color, #2563eb)';
                editBtn.style.marginRight = '8px';
                editBtn.textContent = 'Edit Date';
                editBtn.onclick = () => openEditProdLogDateModal(log.id, log.date);
                actionTd.appendChild(editBtn);

                const editMachineBtn = document.createElement('button');
                editMachineBtn.className = 'btn-text';
                editMachineBtn.style.color = 'var(--primary-color, #2563eb)';
                editMachineBtn.style.marginRight = '8px';
                editMachineBtn.textContent = 'Edit Machine';
                editMachineBtn.onclick = () => openEditProdLogMachineModal(log.id, log.machine, log.dept);
                actionTd.appendChild(editMachineBtn);

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
            applyProdLogHeaderFilters();
        } catch (e) { console.error(e); }
    }

    const prodLogMachineIdle = document.getElementById('prodLogMachineIdle');
    const prodLogProdFields = document.getElementById('prodLogProdFields');

    function toggleMachineIdleMode() {
        if (!prodLogMachineIdle || !prodLogProdFields) return;
        const isIdle = prodLogMachineIdle.value === 'y';
        if (isIdle) {
            prodLogProdFields.style.display = 'none';
            ['prodLogOperator', 'prodLogPartNo', 'prodLogOpnNo', 'prodLogRuntime', 'prodLogProdQty'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.removeAttribute('required');
            });
        } else {
            prodLogProdFields.style.display = 'grid';
            ['prodLogOperator', 'prodLogPartNo', 'prodLogOpnNo', 'prodLogRuntime', 'prodLogProdQty'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.setAttribute('required', 'required');
            });
        }
        validateHours();
    }

    if (prodLogMachineIdle) {
        prodLogMachineIdle.addEventListener('change', toggleMachineIdleMode);
    }

    const prodLogForm = document.getElementById('prodLogForm');
    if (prodLogForm) {
        prodLogForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const isIdle = document.getElementById('prodLogMachineIdle') ? document.getElementById('prodLogMachineIdle').value === 'y' : false;

            if (isIdle) {
                const idleHrs = parseFloat(document.getElementById('prodLogIdleHours').value) || 0;
                const idleRsn = document.getElementById('prodLogIdleReason').value;
                if (idleHrs <= 0) {
                    alert('Please enter Idle Hours for the idle machine.');
                    return;
                }
                if (!idleRsn || idleRsn === 'None') {
                    alert('Please select an Idle Reason.');
                    return;
                }
            }

            const data = {
                dept: document.getElementById('prodLogDept').value,
                date: document.getElementById('prodLogDate').value,
                shift: document.getElementById('prodLogShift').value,
                setter: document.getElementById('prodLogSetter').value,
                machine: document.getElementById('prodLogMachine').value,
                operator: isIdle ? "" : document.getElementById('prodLogOperator').value,
                multiple_mc: isIdle ? 1 : (parseInt(document.getElementById('prodLogMultipleMc').value) || 1),
                partno: isIdle ? "MACHINE IDLE" : document.getElementById('prodLogPartNo').value,
                opn_no: isIdle ? "IDLE" : document.getElementById('prodLogOpnNo').value,
                description: isIdle ? (document.getElementById('prodLogIdleReason').value || "Machine Idle") : document.getElementById('prodLogDescription').value,
                cycle_time: isIdle ? 0 : (parseFloat(document.getElementById('prodLogCycleTime').value) || 0),
                runtime: isIdle ? 0 : (parseFloat(document.getElementById('prodLogRuntime').value) || 0),
                target_qty: isIdle ? 0 : (parseFloat(document.getElementById('prodLogTargetQty').value) || 0),
                prod_qty: isIdle ? 0 : (parseFloat(document.getElementById('prodLogProdQty').value) || 0),
                efficiency: isIdle ? 0 : (parseFloat(document.getElementById('prodLogEfficiency').value) || 0),
                idle_hours: parseFloat(document.getElementById('prodLogIdleHours').value) || 0,
                idle_reason: document.getElementById('prodLogIdleReason').value,
                idle_hours_2: isIdle ? 0 : (parseFloat(document.getElementById('prodLogIdleHours2').value) || 0),
                idle_reason_2: isIdle ? "None" : document.getElementById('prodLogIdleReason2').value,
                idle_hours_3: isIdle ? 0 : (parseFloat(document.getElementById('prodLogIdleHours3').value) || 0),
                idle_reason_3: isIdle ? "None" : document.getElementById('prodLogIdleReason3').value
            };
            
            try {
                const response = await fetch('/api/prodlog', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (response.ok) {
                    alert(isIdle ? 'Machine Idle Log saved successfully!' : 'Production Log saved!');
                    
                    const continueOp = document.getElementById('prodLogContinueOperator') ? document.getElementById('prodLogContinueOperator').value : 'n';
                    
                    if (continueOp === 'y' && !isIdle) {
                        const savedDept = data.dept;
                        const savedDate = data.date;
                        const savedShift = data.shift;
                        const savedSetter = data.setter;
                        const savedOperator = data.operator;
                        
                        prodLogForm.reset();
                        
                        document.getElementById('prodLogDept').value = savedDept;
                        document.getElementById('prodLogDate').value = savedDate;
                        document.getElementById('prodLogShift').value = savedShift;
                        document.getElementById('prodLogSetter').value = savedSetter;
                        document.getElementById('prodLogOperator').value = savedOperator;
                        document.getElementById('prodLogContinueOperator').value = 'y';
                        currentOperatorSessionHours += (
                            (parseFloat(data.runtime) || 0) + 
                            (parseFloat(data.idle_hours) || 0) + 
                            (parseFloat(data.idle_hours_2) || 0) + 
                            (parseFloat(data.idle_hours_3) || 0)
                        );
                    } else {
                        currentOperatorSessionHours = 0;
                        const savedDate = document.getElementById('prodLogDate').value;
                        prodLogForm.reset();
                        if (savedDate) document.getElementById('prodLogDate').value = savedDate;
                        else document.getElementById('prodLogDate').valueAsDate = new Date();
                        if (document.getElementById('prodLogContinueOperator')) {
                            document.getElementById('prodLogContinueOperator').value = 'n';
                        }
                    }
                    toggleMachineIdleMode();
                    validateHours();
                    
                    fetchProdLogs();
                } else {
                    alert('Error saving Prod Log');
                }
            } catch (err) { console.error(err); }
        });
    }

    document.addEventListener('input', (e) => {
        if (e.target && e.target.classList.contains('prod-log-col-filter')) {
            applyProdLogHeaderFilters();
        }
    });

    function applyProdLogHeaderFilters() {
        const filters = {};
        document.querySelectorAll('.prod-log-col-filter').forEach(input => {
            const val = input.value.trim().toLowerCase();
            if (val) {
                filters[input.getAttribute('data-col')] = val;
            }
        });

        const rows = document.querySelectorAll('#prodLogBody tr');
        rows.forEach(tr => {
            const cells = tr.children;
            let show = true;
            for (const colIdx in filters) {
                const cell = cells[parseInt(colIdx)];
                if (cell) {
                    const cellText = (cell.textContent || '').trim().toLowerCase();
                    if (!cellText.includes(filters[colIdx])) {
                        show = false;
                        break;
                    }
                }
            }
            tr.style.display = show ? '' : 'none';
        });
    }

    const prodLogTableFilterDate = document.getElementById('prodLogTableFilterDate');
    const clearProdLogFilterDateBtn = document.getElementById('clearProdLogFilterDateBtn');

    if (prodLogTableFilterDate) {
        prodLogTableFilterDate.addEventListener('change', (e) => {
            const dateVal = e.target.value;
            const dateHeaderInput = document.querySelector('.prod-log-col-filter[data-col="0"]');
            if (dateHeaderInput) {
                if (dateVal) {
                    const parts = dateVal.split('-');
                    const fmtDate = `${parts[2]}/${parts[1]}`;
                    dateHeaderInput.value = fmtDate;
                } else {
                    dateHeaderInput.value = '';
                }
                applyProdLogHeaderFilters();
            }
        });
    }

    if (clearProdLogFilterDateBtn) {
        clearProdLogFilterDateBtn.addEventListener('click', () => {
            if (prodLogTableFilterDate) prodLogTableFilterDate.value = '';
            const dateHeaderInput = document.querySelector('.prod-log-col-filter[data-col="0"]');
            if (dateHeaderInput) dateHeaderInput.value = '';
            applyProdLogHeaderFilters();
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

    // --- Edit Prod Log Date Modal Logic ---
    const editProdLogDateModal = document.getElementById('editProdLogDateModal');
    const editProdLogDateForm = document.getElementById('editProdLogDateForm');
    const closeEditProdLogDateModalBtn = document.getElementById('closeEditProdLogDateModalBtn');
    const cancelEditProdLogDateBtn = document.getElementById('cancelEditProdLogDateBtn');

    function openEditProdLogDateModal(logId, currentDate) {
        if (!editProdLogDateModal) return;
        document.getElementById('editProdLogId').value = logId;
        document.getElementById('editProdLogDateInput').value = currentDate || new Date().toISOString().split('T')[0];
        editProdLogDateModal.classList.add('show');
    }

    function closeEditProdLogDateModal() {
        if (editProdLogDateModal) editProdLogDateModal.classList.remove('show');
    }

    if (closeEditProdLogDateModalBtn) closeEditProdLogDateModalBtn.addEventListener('click', closeEditProdLogDateModal);
    if (cancelEditProdLogDateBtn) cancelEditProdLogDateBtn.addEventListener('click', closeEditProdLogDateModal);

    if (editProdLogDateForm) {
        editProdLogDateForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const logId = document.getElementById('editProdLogId').value;
            const newDate = document.getElementById('editProdLogDateInput').value;
            if (!logId || !newDate) return;

            try {
                const res = await fetch(`/api/prodlog/${logId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ date: newDate })
                });
                if (res.ok) {
                    closeEditProdLogDateModal();
                    fetchProdLogs();
                } else {
                    alert('Failed to update log date.');
                }
            } catch (err) {
                console.error(err);
                alert('Error updating log date.');
            }
        });
    }

    // --- Edit Prod Log Machine Modal Logic ---
    const editProdLogMachineModal = document.getElementById('editProdLogMachineModal');
    const editProdLogMachineForm = document.getElementById('editProdLogMachineForm');
    const closeEditProdLogMachineModalBtn = document.getElementById('closeEditProdLogMachineModalBtn');
    const cancelEditProdLogMachineBtn = document.getElementById('cancelEditProdLogMachineBtn');

    async function openEditProdLogMachineModal(logId, currentMachine, dept) {
        if (!editProdLogMachineModal) return;
        document.getElementById('editProdLogMachineId').value = logId;
        
        if (!prodLogAllMachines || prodLogAllMachines.length === 0) {
            try {
                const machRes = await fetch('/api/machines');
                prodLogAllMachines = await machRes.json();
            } catch(e) { console.error(e); }
        }
        
        const select = document.getElementById('editProdLogMachineSelect');
        select.innerHTML = '<option value="">-- Select Machine --</option>';
        
        const cleanDept = (dept || '').trim().toUpperCase();
        let filteredMachines = prodLogAllMachines;
        if (cleanDept) {
            const matches = prodLogAllMachines.filter(m => (m.department || '').trim().toUpperCase() === cleanDept);
            if (matches.length > 0) filteredMachines = matches;
        }
        
        filteredMachines.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.name;
            opt.textContent = m.name;
            if (m.name === currentMachine) opt.selected = true;
            select.appendChild(opt);
        });

        editProdLogMachineModal.classList.add('show');
    }

    function closeEditProdLogMachineModal() {
        if (editProdLogMachineModal) editProdLogMachineModal.classList.remove('show');
    }

    if (closeEditProdLogMachineModalBtn) closeEditProdLogMachineModalBtn.addEventListener('click', closeEditProdLogMachineModal);
    if (cancelEditProdLogMachineBtn) cancelEditProdLogMachineBtn.addEventListener('click', closeEditProdLogMachineModal);

    if (editProdLogMachineForm) {
        editProdLogMachineForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const logId = document.getElementById('editProdLogMachineId').value;
            const newMachine = document.getElementById('editProdLogMachineSelect').value;
            if (!logId || !newMachine) return;

            try {
                const res = await fetch(`/api/prodlog/${logId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ machine: newMachine })
                });
                if (res.ok) {
                    closeEditProdLogMachineModal();
                    fetchProdLogs();
                } else {
                    alert('Failed to update log machine.');
                }
            } catch (err) {
                console.error(err);
                alert('Error updating log machine.');
            }
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
                    let extraCols = '';
                    if (type === 'despatch') {
                        extraCols = `
                            <td>${log.finish_part_no || '-'}</td>
                            <td>${log.dc_no || '-'}</td>
                        `;
                    }
                    tr.innerHTML = `
                        <td>${log.date}</td>
                        <td>${log.forge_pn}</td>
                        ${extraCols}
                        <td>${log.qty}</td>
                        <td>
                            <button class="btn btn-outline" style="padding: 0.25rem 0.5rem; font-size: 0.8rem; color: #ef4444; border-color: #ef4444;" onclick="deleteRmLog(${log.id}, '${type}')">Delete</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        } catch (e) {
            console.error(e);
        }
    }

    window.deleteRmLog = async (id, type) => {
        if (confirm('Are you sure you want to delete this record?')) {
            try {
                const res = await fetch(`/api/rawmateriallogs/${id}`, { method: 'DELETE' });
                if (res.ok) {
                    fetchRmLogs(type);
                    if (typeof fetchRawMaterials === 'function') fetchRawMaterials();
                } else {
                    alert('Failed to delete log record');
                }
            } catch (e) {
                console.error(e);
            }
        }
    };

    // --- RAW MATERIAL LOGIC ---
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
            const dc_no = type === 'despatch' ? document.getElementById('rmLogDcNo').value : null;
            const finish_part_no = type === 'despatch' ? document.getElementById('rmLogFinishPartNo').value : null;
            const qty = parseInt(document.getElementById('rmLogQty').value) || 0;
            
            const payload = { type, date, forge_pn, dc_no, finish_part_no, qty };
            
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
    let allUsersList = [];

    async function fetchUsers() {
        try {
            const res = await fetch('/api/users');
            allUsersList = await res.json();
            const tbody = document.getElementById('usersBody');
            if (!tbody) return;
            tbody.innerHTML = '';
            allUsersList.forEach(u => {
                const tr = document.createElement('tr');
                tr.style.cursor = 'pointer';
                tr.title = 'Click to view & edit rights';
                tr.innerHTML = `
                    <td>${u.id}</td>
                    <td><strong>${u.username}</strong></td>
                    <td>${u.role}</td>
                    <td>
                        <button class="btn btn-outline edit-user-btn" style="margin-right: 5px; padding: 0.3rem 0.6rem; font-size: 0.85rem;">Edit Rights</button>
                        <button class="btn btn-outline" style="margin-right: 5px; padding: 0.3rem 0.6rem; font-size: 0.85rem;" onclick="event.stopPropagation(); openChangePasswordModal(${u.id}, '${u.username}')">Change Password</button>
                        ${u.username !== 'admin' ? `<button class="btn btn-danger" style="padding: 0.3rem 0.6rem; font-size: 0.85rem;" onclick="event.stopPropagation(); deleteUser(${u.id})">Delete</button>` : ''}
                    </td>
                `;

                tr.addEventListener('click', () => populateUserRightsForm(u));
                tr.querySelector('.edit-user-btn')?.addEventListener('click', (e) => {
                    e.stopPropagation();
                    populateUserRightsForm(u);
                });

                tbody.appendChild(tr);
            });
        } catch (e) { console.error(e); }
    }

    function populateUserRightsForm(user) {
        document.getElementById('editingUserId').value = user.id;
        document.getElementById('userFormTitle').innerText = `Edit Rights (${user.username})`;
        document.getElementById('userName').value = user.username;
        document.getElementById('userPass').value = '';
        document.getElementById('userPass').removeAttribute('required');
        document.getElementById('userPassLabel').innerText = 'Password (leave blank to keep current)';
        document.getElementById('userSubmitBtn').innerText = 'Save User Rights';
        document.getElementById('resetUserFormBtn').style.display = 'inline-block';

        let screens = [];
        try {
            screens = JSON.parse(user.accessible_screens || '[]');
        } catch(e) {}

        document.querySelectorAll('#userScreensList input[type="checkbox"]').forEach(chk => {
            if (chk.value === 'inventory') {
                chk.checked = screens.includes('inventory') || screens.includes('rawmaterial');
            } else {
                chk.checked = screens.includes(chk.value);
            }
        });
    }

    function resetUserRightsForm() {
        document.getElementById('editingUserId').value = '';
        document.getElementById('userFormTitle').innerText = 'Create User';
        document.getElementById('userName').value = '';
        document.getElementById('userPass').value = '';
        document.getElementById('userPass').setAttribute('required', 'true');
        document.getElementById('userPassLabel').innerText = 'Password';
        document.getElementById('userSubmitBtn').innerText = 'Create User';
        document.getElementById('resetUserFormBtn').style.display = 'none';
        document.querySelectorAll('#userScreensList input[type="checkbox"]').forEach(chk => chk.checked = false);
    }

    document.getElementById('resetUserFormBtn')?.addEventListener('click', resetUserRightsForm);

    const userCreateForm = document.getElementById('userCreateForm');
    if (userCreateForm) {
        userCreateForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const editingId = document.getElementById('editingUserId').value;
            const username = document.getElementById('userName').value.trim();
            const password = document.getElementById('userPass').value.trim();

            const selectedScreens = Array.from(document.querySelectorAll('#userScreensList input[type="checkbox"]:checked')).map(cb => cb.value);
            const screensJson = JSON.stringify(selectedScreens);

            if (editingId) {
                const payload = {
                    username: username,
                    accessible_screens: screensJson
                };
                if (password) payload.password = password;

                try {
                    const res = await fetch(`/api/users/${editingId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    if (res.ok) {
                        alert(`Rights updated for ${username}!`);
                        resetUserRightsForm();
                        fetchUsers();
                    } else {
                        const errData = await res.json();
                        alert(errData.detail || 'Error updating user');
                    }
                } catch(err) {
                    console.error(err);
                    alert('Error updating user');
                }
            } else {
                if (!password) {
                    alert('Password is required for new users.');
                    return;
                }
                const payload = {
                    username: username,
                    password: password,
                    accessible_screens: screensJson
                };

                try {
                    const res = await fetch('/api/users', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    if (res.ok) {
                        alert('User created successfully!');
                        resetUserRightsForm();
                        fetchUsers();
                    } else {
                        const errData = await res.json();
                        alert(errData.detail || 'Error creating user');
                    }
                } catch(err) {
                    console.error(err);
                    alert('Error creating user');
                }
            }
        });
    }

    window.openChangePasswordModal = (userId, username) => {
        const modal = document.getElementById('changePasswordModal');
        if (!modal) return;
        document.getElementById('changePasswordUserId').value = userId;
        document.getElementById('changePasswordModalTitle').innerText = `Change Password for ${username}`;
        document.getElementById('newPasswordInput').value = '';
        modal.classList.add('show');
    };

    const changePasswordForm = document.getElementById('changePasswordForm');
    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const userId = document.getElementById('changePasswordUserId').value;
            const newPassword = document.getElementById('newPasswordInput').value.trim();

            if (!newPassword) {
                alert('Please enter a new password');
                return;
            }

            try {
                const res = await fetch(`/api/users/${userId}/password`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ new_password: newPassword })
                });

                if (res.ok) {
                    alert('Password updated successfully!');
                    document.getElementById('changePasswordModal').classList.remove('show');
                } else {
                    const data = await res.json();
                    alert(data.detail || 'Error updating password');
                }
            } catch (err) {
                console.error(err);
                alert('Error updating password');
            }
        });
    }

    document.getElementById('closeChangePasswordModalBtn')?.addEventListener('click', () => {
        document.getElementById('changePasswordModal').classList.remove('show');
    });
    document.getElementById('cancelChangePasswordBtn')?.addEventListener('click', () => {
        document.getElementById('changePasswordModal').classList.remove('show');
    });
    
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




    // ====== DEPARTMENTS CRUD ======
    async function fetchDepartments() {
        try {
            const res = await fetch('/api/departments');
            if (res.ok) {
                const depts = await res.json();
                renderDepartments(depts);
                populateDeptDropdowns(depts); // Also update dropdowns whenever departments are fetched
            }
        } catch (e) { console.error('Error fetching departments', e); }
    }

    function renderDepartments(depts) {
        const tbody = document.getElementById('departmentsBody');
        tbody.innerHTML = '';
        depts.forEach(d => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${d.id}</td>
                <td>${d.name}</td>
                <td class="actions-cell">
                    <button class="btn btn-outline edit-dept-btn" data-id="${d.id}" data-name="${d.name}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem;">Edit</button>
                    <button class="btn btn-outline delete-dept-btn" data-id="${d.id}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem; color: #ef4444; border-color: #ef4444;">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        document.querySelectorAll('.edit-dept-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.getAttribute('data-id');
                const name = e.target.getAttribute('data-name');
                openDeptModal({ id, name });
            });
        });

        document.querySelectorAll('.delete-dept-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                if (confirm('Delete this department?')) {
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/departments/${id}`, { method: 'DELETE' });
                        if (res.ok) fetchDepartments();
                        else alert('Error deleting department');
                    } catch (err) { console.error(err); }
                }
            });
        });
    }

    function openDeptModal(dept = null) {
        if (dept) {
            deptModalTitle.textContent = 'Edit Department';
            deptIdInput.value = dept.id;
            deptNameInput.value = dept.name;
        } else {
            deptModalTitle.textContent = 'Add Department';
            deptForm.reset();
            deptIdInput.value = '';
        }
        deptModal.classList.add('show');
    }

    if (cancelDeptBtn) {
        cancelDeptBtn.addEventListener('click', () => {
            deptModal.classList.remove('show');
        });
    }

    if (deptForm) {
        deptForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                name: deptNameInput.value
            };
            const id = deptIdInput.value;
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/departments/${id}` : '/api/departments';

            try {
                const res = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    deptModal.classList.remove('show');
                    fetchDepartments();
                } else {
                    alert('Error saving department');
                }
            } catch (err) {
                console.error(err);
                alert('Error saving department');
            }
        });
    }

    function populateDeptDropdowns(depts) {
        const selects = [
            'scheduleDept', 'statusDeptSelect', 'deburDeptSelect', 
            'inspDeptSelect', 'prodLogDept', 'partDept', 'machineDept', 'operEffDept'
        ];
        
        selects.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                const currentVal = el.value;
                let html = '<option value="">-- Select Dept --</option>';
                depts.forEach(d => {
                    html += `<option value="${d.name}">${d.name}</option>`;
                });
                el.innerHTML = html;
                if (currentVal && depts.find(d => d.name === currentVal)) {
                    el.value = currentVal;
                }
            }
        });

        // mcUtilDept has a different first option "-- All Departments --"
        const mcUtilDept = document.getElementById('mcUtilDept');
        if (mcUtilDept) {
            const currentVal = mcUtilDept.value;
            let html = '<option value="">-- All Departments --</option>';
            depts.forEach(d => {
                html += `<option value="${d.name}">${d.name}</option>`;
            });
            mcUtilDept.innerHTML = html;
            if (currentVal && depts.find(d => d.name === currentVal)) {
                mcUtilDept.value = currentVal;
            }
        }
    }
    
    // ====== SHIFT CRUD ======
    async function fetchShifts() {
        try {
            const res = await fetch('/api/shifts');
            const data = await res.json();
            allShifts = data;
            renderShifts(data);
            populateShiftDropdowns(data);
        } catch (err) { console.error(err); }
    }

    function renderShifts(shifts) {
        const tbody = document.getElementById('shiftsBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        shifts.forEach(s => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${s.id}</td>
                <td>${s.name}</td>
                <td>${s.hours}</td>
                <td class="actions-cell">
                    <button class="btn btn-outline edit-shift-btn" data-id="${s.id}" data-name="${s.name}" data-hours="${s.hours}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem;">Edit</button>
                    <button class="btn btn-outline delete-shift-btn" data-id="${s.id}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem; color: #ef4444; border-color: #ef4444;">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        document.querySelectorAll('.edit-shift-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.getAttribute('data-id');
                const name = e.target.getAttribute('data-name');
                const hours = e.target.getAttribute('data-hours');
                openShiftModal({ id, name, hours });
            });
        });

        document.querySelectorAll('.delete-shift-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                if (confirm('Delete this shift?')) {
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/shifts/${id}`, { method: 'DELETE' });
                        if (res.ok) fetchShifts();
                        else alert('Error deleting shift');
                    } catch (err) { console.error(err); }
                }
            });
        });
    }

    function openShiftModal(shift = null) {
        if (!shiftModal) return;
        if (shift) {
            shiftModalTitle.textContent = 'Edit Shift';
            shiftIdInput.value = shift.id;
            shiftNameInput.value = shift.name;
            shiftHoursInput.value = shift.hours;
        } else {
            shiftModalTitle.textContent = 'Add Shift';
            shiftForm.reset();
            shiftIdInput.value = '';
        }
        shiftModal.classList.add('show');
    }

    if (cancelShiftBtn) {
        cancelShiftBtn.addEventListener('click', () => {
            shiftModal.classList.remove('show');
        });
    }

    if (shiftForm) {
        shiftForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                name: shiftNameInput.value,
                hours: parseFloat(shiftHoursInput.value) || 8.0
            };
            const id = shiftIdInput.value;
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/shifts/${id}` : '/api/shifts';

            try {
                const res = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    shiftModal.classList.remove('show');
                    fetchShifts();
                } else {
                    alert('Error saving shift');
                }
            } catch (err) {
                console.error(err);
                alert('Error saving shift');
            }
        });
    }

    function populateShiftDropdowns(shifts) {
        const selects = ['scheduleRunShift', 'prodLogShift'];
        
        selects.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                const currentVal = el.value;
                let html = '<option value="">-- Select Shift --</option>';
                shifts.forEach(s => {
                    html += `<option value="${s.name}">${s.name} (${s.hours} Hrs)</option>`;
                });
                el.innerHTML = html;
                if (currentVal && shifts.find(s => s.name === currentVal)) {
                    el.value = currentVal;
                }
            }
        });
    }
    
    // Initial fetch to populate dropdowns on page load
    fetchDepartments();
    fetchShifts();
    fetchVendors();

    // ====== VENDOR CRUD ======
    const vendorModal = document.getElementById('vendorModal');
    const vendorForm = document.getElementById('vendorForm');
    const vendorIdInput = document.getElementById('vendorId');
    const vendorNameInput = document.getElementById('vendorName');
    const vendorDetailsInput = document.getElementById('vendorDetails');
    const vendorModalTitle = document.getElementById('vendorModalTitle');
    const cancelVendorBtn = document.getElementById('cancelVendorBtn');
    const closeVendorModalBtn = document.getElementById('closeVendorModalBtn');

    async function fetchVendors() {
        try {
            const res = await fetch('/api/vendors');
            const data = await res.json();
            renderVendors(data);
        } catch (err) { console.error(err); }
    }

    function renderVendors(vendors) {
        const tbody = document.getElementById('vendorsBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        vendors.forEach(v => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${v.id}</td>
                <td>${v.name}</td>
                <td>${v.details || ''}</td>
                <td class="actions-cell">
                    <button class="btn btn-outline edit-vendor-btn" data-id="${v.id}" data-name="${v.name}" data-details="${v.details || ''}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem;">Edit</button>
                    <button class="btn btn-outline delete-vendor-btn" data-id="${v.id}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem; color: #ef4444; border-color: #ef4444;">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        document.querySelectorAll('.edit-vendor-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.getAttribute('data-id');
                const name = e.target.getAttribute('data-name');
                const details = e.target.getAttribute('data-details');
                openVendorModal({ id, name, details });
            });
        });

        document.querySelectorAll('.delete-vendor-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                if (confirm('Delete this vendor?')) {
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/vendors/${id}`, { method: 'DELETE' });
                        if (res.ok) fetchVendors();
                        else alert('Error deleting vendor');
                    } catch (err) { console.error(err); }
                }
            });
        });
    }

    function openVendorModal(vendor = null) {
        if (!vendorModal) return;
        if (vendor) {
            vendorModalTitle.textContent = 'Edit Vendor';
            vendorIdInput.value = vendor.id;
            vendorNameInput.value = vendor.name;
            vendorDetailsInput.value = vendor.details;
        } else {
            vendorModalTitle.textContent = 'Add Vendor';
            vendorForm.reset();
            vendorIdInput.value = '';
        }
        vendorModal.classList.add('show');
    }

    if (cancelVendorBtn) {
        cancelVendorBtn.addEventListener('click', () => {
            vendorModal.classList.remove('show');
        });
    }
    if (closeVendorModalBtn) {
        closeVendorModalBtn.addEventListener('click', () => {
            vendorModal.classList.remove('show');
        });
    }

    if (vendorForm) {
        vendorForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                name: vendorNameInput.value,
                details: vendorDetailsInput.value
            };
            const id = vendorIdInput.value;
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/vendors/${id}` : '/api/vendors';

            try {
                const res = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    vendorModal.classList.remove('show');
                    fetchVendors();
                } else {
                    alert('Error saving vendor');
                }
            } catch (err) {
                console.error(err);
                alert('Error saving vendor');
            }
        });
    }

    // ====== HT LOG CRUD ======
    const htModal = document.getElementById('htModal');
    const htForm = document.getElementById('htForm');
    const htDateInput = document.getElementById('htDate');
    const htDcNoInput = document.getElementById('htDcNo');
    const htVendorSelect = document.getElementById('htVendor');
    const htPartNoSelect = document.getElementById('htPartNo');
    const htAvailableQtyInput = document.getElementById('htAvailableQty');
    const htQtyInput = document.getElementById('htQty');
    const cancelHtBtn = document.getElementById('cancelHtBtn');
    const closeHtModalBtn = document.getElementById('closeHtModalBtn');

    let currentSpiderParts = [];
    let currentVendorPending = [];

    async function fetchHtData() {
        await Promise.all([
            fetchAvailableHtParts(),
            fetchHtLogs(),
            fetchHtVendorPendingParts(),
            fetchHtReceiptLogs()
        ]);
    }

    async function fetchAvailableHtParts() {
        try {
            const res = await fetch('/api/ht/spider_parts');
            const data = await res.json();
            currentSpiderParts = data;
            renderAvailableHtParts(data);
        } catch (err) { console.error(err); }
    }

    function renderAvailableHtParts(parts) {
        const tbody = document.getElementById('htAvailablePartsBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        
        // Filter out parts with available_qty <= 0
        const availableParts = (parts || []).filter(p => (p.available_qty || 0) > 0);

        if (!availableParts || availableParts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 0.75rem;">No SPIDER parts with available Opn 40 quantity found</td></tr>';
            return;
        }
        availableParts.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${p.partno}</strong></td>
                <td>${p.department || 'SPIDER'}</td>
                <td>${p.produced_qty}</td>
                <td>${p.ht_sent_qty}</td>
                <td><span style="font-weight: bold; color: #16a34a;">${p.available_qty}</span></td>
                <td>
                    <button class="btn btn-primary send-part-ht-btn" data-partno="${p.partno}" style="padding: 0.2rem 0.5rem; font-size: 0.8rem;">
                        Send to HT
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        document.querySelectorAll('.send-part-ht-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const partno = e.currentTarget.getAttribute('data-partno');
                openHtModal(partno);
            });
        });
    }

    async function fetchHtLogs() {
        try {
            const res = await fetch('/api/ht_logs');
            const data = await res.json();
            renderHtLogs(data);
        } catch (err) { console.error(err); }
    }

    function renderHtLogs(logs) {
        const tbody = document.getElementById('htBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!logs || logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 0.75rem;">No HT dispatch records found</td></tr>';
            return;
        }
        logs.forEach(l => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${l.id}</td>
                <td>${l.date}</td>
                <td>${l.dc_no || ''}</td>
                <td>${l.vendor}</td>
                <td>${l.partno}</td>
                <td>${l.qty}</td>
                <td class="actions-cell">
                    <button class="btn btn-outline delete-ht-btn" data-id="${l.id}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem; color: #ef4444; border-color: #ef4444;">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        document.querySelectorAll('.delete-ht-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                if (confirm('Delete this HT record?')) {
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/ht_logs/${id}`, { method: 'DELETE' });
                        if (res.ok) fetchHtData();
                        else alert('Error deleting HT record');
                    } catch (err) { console.error(err); }
                }
            });
        });
    }

    async function openHtModal(preselectedPartNo = null) {
        if (!htModal) return;
        htForm.reset();
        htAvailableQtyInput.value = '0';
        
        // Retain current date or set to today
        if (!htDateInput.value) {
            htDateInput.valueAsDate = new Date();
        }

        // Fetch vendors
        try {
            const vRes = await fetch('/api/vendors');
            const vendors = await vRes.json();
            let vHtml = '<option value="">-- Select Vendor --</option>';
            vendors.forEach(v => {
                vHtml += `<option value="${v.name}">${v.name}</option>`;
            });
            htVendorSelect.innerHTML = vHtml;
        } catch (err) { console.error(err); }

        // Fetch SPIDER parts
        try {
            const pRes = await fetch('/api/ht/spider_parts');
            const allParts = await pRes.json();
            currentSpiderParts = allParts.filter(p => (p.available_qty || 0) > 0 || p.partno === preselectedPartNo);
            let pHtml = '<option value="">-- Select Part --</option>';
            currentSpiderParts.forEach(p => {
                pHtml += `<option value="${p.partno}">${p.partno} (Avail: ${p.available_qty})</option>`;
            });
            htPartNoSelect.innerHTML = pHtml;

            if (preselectedPartNo) {
                htPartNoSelect.value = preselectedPartNo;
                const found = currentSpiderParts.find(p => p.partno === preselectedPartNo);
                htAvailableQtyInput.value = found ? found.available_qty : 0;
            }
        } catch (err) { console.error(err); }

        htModal.classList.add('show');
    }

    if (htPartNoSelect) {
        htPartNoSelect.addEventListener('change', (e) => {
            const partno = e.target.value;
            const found = currentSpiderParts.find(p => p.partno === partno);
            htAvailableQtyInput.value = found ? found.available_qty : 0;
        });
    }

    if (cancelHtBtn) {
        cancelHtBtn.addEventListener('click', () => htModal.classList.remove('show'));
    }
    if (closeHtModalBtn) {
        closeHtModalBtn.addEventListener('click', () => htModal.classList.remove('show'));
    }

    if (htForm) {
        htForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const partno = htPartNoSelect.value;
            const qty = parseInt(htQtyInput.value) || 0;
            const avail = parseInt(htAvailableQtyInput.value) || 0;

            if (qty > avail) {
                if (!confirm(`Warning: Entered quantity (${qty}) is greater than available Opn 50 quantity (${avail}). Do you still want to proceed?`)) {
                    return;
                }
            }

            const payload = {
                date: htDateInput.value,
                dc_no: htDcNoInput.value,
                vendor: htVendorSelect.value,
                partno: partno,
                qty: qty
            };

            try {
                const res = await fetch('/api/ht_logs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    htModal.classList.remove('show');
                    fetchHtData();
                } else {
                    alert('Error saving HT record');
                }
            } catch (err) {
                console.error(err);
                alert('Error saving HT record');
            }
        });
    }

    // ====== HT RECEIPT LOG CRUD ======
    const htReceiptModal = document.getElementById('htReceiptModal');
    const htReceiptForm = document.getElementById('htReceiptForm');
    const htReceiptDateInput = document.getElementById('htReceiptDate');
    const htReceiptVendorSelect = document.getElementById('htReceiptVendor');
    const htReceiptPartNoSelect = document.getElementById('htReceiptPartNo');
    const htReceiptPendingQtyInput = document.getElementById('htReceiptPendingQty');
    const htReceiptQtyInput = document.getElementById('htReceiptQty');
    const cancelHtReceiptBtn = document.getElementById('cancelHtReceiptBtn');
    const closeHtReceiptModalBtn = document.getElementById('closeHtReceiptModalBtn');

    async function fetchHtVendorPendingParts() {
        try {
            const res = await fetch('/api/ht/vendor_pending_parts');
            const data = await res.json();
            currentVendorPending = data;
            renderHtVendorPendingParts(data);
        } catch (err) { console.error(err); }
    }

    function renderHtVendorPendingParts(pendingList) {
        const tbody = document.getElementById('htVendorPendingBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        const activePending = (pendingList || []).filter(p => p.pending_qty > 0);
        
        if (activePending.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 0.75rem;">No parts currently pending at HT vendors</td></tr>';
            return;
        }

        activePending.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${p.vendor}</strong></td>
                <td>${p.partno}</td>
                <td>${p.sent_qty}</td>
                <td>${p.received_qty}</td>
                <td><span style="font-weight: bold; color: #d97706;">${p.pending_qty}</span></td>
                <td>
                    <button class="btn btn-primary receive-part-ht-btn" data-vendor="${p.vendor}" data-partno="${p.partno}" style="padding: 0.2rem 0.5rem; font-size: 0.8rem; background-color: #059669; border-color: #059669;">
                        Receive from HT
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        document.querySelectorAll('.receive-part-ht-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const vendor = e.currentTarget.getAttribute('data-vendor');
                const partno = e.currentTarget.getAttribute('data-partno');
                openHtReceiptModal(vendor, partno);
            });
        });
    }

    async function fetchHtReceiptLogs() {
        try {
            const res = await fetch('/api/ht_receipt_logs');
            const data = await res.json();
            renderHtReceiptLogs(data);
        } catch (err) { console.error(err); }
    }

    function renderHtReceiptLogs(logs) {
        const tbody = document.getElementById('htReceiptBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!logs || logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 0.75rem;">No HT receipt records found</td></tr>';
            return;
        }
        logs.forEach(l => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${l.id}</td>
                <td>${l.date}</td>
                <td>${l.vendor}</td>
                <td>${l.partno}</td>
                <td><span style="font-weight: bold; color: #059669;">+${l.qty}</span></td>
                <td class="actions-cell">
                    <button class="btn btn-outline delete-ht-receipt-btn" data-id="${l.id}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem; color: #ef4444; border-color: #ef4444;">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        document.querySelectorAll('.delete-ht-receipt-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                if (confirm('Delete this HT receipt record?')) {
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/ht_receipt_logs/${id}`, { method: 'DELETE' });
                        if (res.ok) fetchHtData();
                        else alert('Error deleting HT receipt record');
                    } catch (err) { console.error(err); }
                }
            });
        });
    }

    async function openHtReceiptModal(preVendor = null, prePartNo = null) {
        if (!htReceiptModal) return;
        htReceiptForm.reset();
        htReceiptPendingQtyInput.value = '0';

        if (!htReceiptDateInput.value) {
            htReceiptDateInput.valueAsDate = new Date();
        }

        // Fetch vendor pending list
        try {
            const res = await fetch('/api/ht/vendor_pending_parts');
            currentVendorPending = await res.json();
            
            // Populate Vendors dropdown (unique vendors with pending > 0)
            const uniqueVendors = [...new Set(currentVendorPending.filter(p => p.pending_qty > 0).map(p => p.vendor))];
            let vHtml = '<option value="">-- Select Vendor --</option>';
            uniqueVendors.forEach(v => {
                vHtml += `<option value="${v}">${v}</option>`;
            });
            htReceiptVendorSelect.innerHTML = vHtml;

            if (preVendor) {
                htReceiptVendorSelect.value = preVendor;
                updateHtReceiptPartsDropdown(preVendor, prePartNo);
            }
        } catch (err) { console.error(err); }

        htReceiptModal.classList.add('show');
    }

    function updateHtReceiptPartsDropdown(vendor, prePartNo = null) {
        const matching = currentVendorPending.filter(p => p.vendor === vendor && p.pending_qty > 0);
        let pHtml = '<option value="">-- Select Part --</option>';
        matching.forEach(m => {
            pHtml += `<option value="${m.partno}">${m.partno} (Pending: ${m.pending_qty})</option>`;
        });
        htReceiptPartNoSelect.innerHTML = pHtml;

        if (prePartNo) {
            htReceiptPartNoSelect.value = prePartNo;
            const found = matching.find(m => m.partno === prePartNo);
            htReceiptPendingQtyInput.value = found ? found.pending_qty : 0;
        } else {
            htReceiptPendingQtyInput.value = '0';
        }
    }

    if (htReceiptVendorSelect) {
        htReceiptVendorSelect.addEventListener('change', (e) => {
            const vendor = e.target.value;
            updateHtReceiptPartsDropdown(vendor);
        });
    }

    if (htReceiptPartNoSelect) {
        htReceiptPartNoSelect.addEventListener('change', (e) => {
            const vendor = htReceiptVendorSelect.value;
            const partno = e.target.value;
            const found = currentVendorPending.find(p => p.vendor === vendor && p.partno === partno);
            htReceiptPendingQtyInput.value = found ? found.pending_qty : 0;
        });
    }

    if (cancelHtReceiptBtn) {
        cancelHtReceiptBtn.addEventListener('click', () => htReceiptModal.classList.remove('show'));
    }
    if (closeHtReceiptModalBtn) {
        closeHtReceiptModalBtn.addEventListener('click', () => htReceiptModal.classList.remove('show'));
    }

    if (htReceiptForm) {
        htReceiptForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const qty = parseInt(htReceiptQtyInput.value) || 0;
            const pending = parseInt(htReceiptPendingQtyInput.value) || 0;

            if (qty > pending) {
                if (!confirm(`Warning: Entered received quantity (${qty}) is greater than pending quantity at vendor (${pending}). Do you still want to proceed?`)) {
                    return;
                }
            }

            const payload = {
                date: htReceiptDateInput.value,
                vendor: htReceiptVendorSelect.value,
                partno: htReceiptPartNoSelect.value,
                qty: qty
            };

            try {
                const res = await fetch('/api/ht_receipt_logs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    htReceiptModal.classList.remove('show');
                    fetchHtData();
                } else {
                    alert('Error saving HT receipt record');
                }
            } catch (err) {
                console.error(err);
                alert('Error saving HT receipt record');
            }
        });
    }

    // ====== M/C UTIL REPORT ======
    const generateMcUtilBtn = document.getElementById('generateMcUtilBtn');
    if (generateMcUtilBtn) {
        generateMcUtilBtn.addEventListener('click', async () => {
            const fromDate = document.getElementById('mcUtilFromDate').value;
            const toDate = document.getElementById('mcUtilToDate').value;
            const dept = document.getElementById('mcUtilDept').value;
            
            if (!fromDate || !toDate) {
                alert('Please select both From and To dates');
                return;
            }

            try {
                const res = await fetch('/api/prodlog');
                const allLogs = await res.json();
                
                // Filter
                const filtered = allLogs.filter(l => {
                    if (dept && (l.dept || '').toUpperCase() !== dept.toUpperCase()) return false;
                    if (l.date < fromDate || l.date > toDate) return false;
                    return true;
                });
                
                // Collect unique idle reasons
                const idleReasonsSet = new Set();
                filtered.forEach(l => {
                    if (l.idle_reason) idleReasonsSet.add(l.idle_reason.trim());
                    if (l.idle_reason_2) idleReasonsSet.add(l.idle_reason_2.trim());
                    if (l.idle_reason_3) idleReasonsSet.add(l.idle_reason_3.trim());
                });
                const idleReasons = Array.from(idleReasonsSet).filter(r => r).sort();
                
                // Group by machine
                const machineData = {};
                filtered.forEach(l => {
                    const mc = (l.machine || 'Unknown').trim();
                    if (!machineData[mc]) {
                        machineData[mc] = { runtime: 0, idleTotal: 0 };
                        idleReasons.forEach(r => machineData[mc][r] = 0);
                    }
                    
                    machineData[mc].runtime += (l.runtime || 0);
                    
                    let idle1 = l.idle_hours || 0;
                    let idle2 = l.idle_hours_2 || 0;
                    let idle3 = l.idle_hours_3 || 0;
                    
                    machineData[mc].idleTotal += (idle1 + idle2 + idle3);
                    
                    if (l.idle_reason && idle1 > 0) machineData[mc][l.idle_reason.trim()] += idle1;
                    if (l.idle_reason_2 && idle2 > 0) machineData[mc][l.idle_reason_2.trim()] += idle2;
                    if (l.idle_reason_3 && idle3 > 0) machineData[mc][l.idle_reason_3.trim()] += idle3;
                });
                
                // Render table
                const thead = document.getElementById('mcUtilHead');
                const tbody = document.getElementById('mcUtilBody');
                
                let headHtml = `<tr>
                    <th>Machine</th>
                    <th>Run Time</th>
                    <th>Idle Time</th>
                    <th>Log Time</th>
                    <th>Util %</th>`;
                idleReasons.forEach(r => {
                    headHtml += `<th>${r}</th>`;
                });
                headHtml += `</tr>`;
                thead.innerHTML = headHtml;
                
                tbody.innerHTML = '';
                
                const sortedMachines = Object.keys(machineData).sort();
                if (sortedMachines.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="${5 + idleReasons.length}" style="text-align:center; color: var(--text-muted);">No data found for selected period</td></tr>`;
                } else {
                    let totalRowHtml = '';
                    sortedMachines.forEach(mc => {
                        const d = machineData[mc];
                        const logTime = d.runtime + d.idleTotal;
                        const utilPercent = (d.runtime / 21) * 100;
                        let rowHtml = `<tr>
                            <td style="font-weight: 500;">${mc}</td>
                            <td>${d.runtime.toFixed(2)}</td>
                            <td>${d.idleTotal.toFixed(2)}</td>
                            <td>${logTime.toFixed(2)}</td>
                            <td>${utilPercent.toFixed(2)}%</td>`;
                        idleReasons.forEach(r => {
                            rowHtml += `<td>${d[r] ? d[r].toFixed(2) : '-'}</td>`;
                        });
                        rowHtml += `</tr>`;
                        totalRowHtml += rowHtml;
                    });
                    tbody.innerHTML = totalRowHtml;
                }
                
            } catch(e) {
                console.error('Error generating M/c Util report:', e);
                alert('Error generating report');
            }
        });
    }

    const exportMcUtilBtn = document.getElementById('exportMcUtilBtn');
    if (exportMcUtilBtn) {
        exportMcUtilBtn.addEventListener('click', () => {
            exportTableToExcel('mcUtilTable', 'Machine_Utilization_Report');
        });
    }

    // --- OPERATOR EFFICIENCY REPORT LOGIC ---
    async function fetchOperEffReport() {
        const selectedDate = document.getElementById('operEffDate')?.value;
        const deptFilter = (document.getElementById('operEffDept')?.value || '').trim().toUpperCase();

        const tbody = document.getElementById('operEffBody');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">Generating report...</td></tr>';

        try {
            const [opRes, prodRes, attRes] = await Promise.all([
                fetch('/api/operators'),
                fetch('/api/prodlog'),
                fetch('/api/attendance')
            ]);

            const allOperators = await opRes.json();
            const allProdLogs = await prodRes.json();
            const allAttendance = await attRes.json();

            let filteredOperators = allOperators;
            if (deptFilter) {
                filteredOperators = allOperators.filter(o => (o.department || '').trim().toUpperCase() === deptFilter);
            }

            tbody.innerHTML = '';
            if (filteredOperators.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">No operators found.</td></tr>';
                return;
            }

            filteredOperators.forEach(op => {
                const opName = (op.name || '').trim();

                // Attendance Hours from Attendance records for selected date
                const opAttRecords = allAttendance.filter(r => (r.employee_name || '').trim().toUpperCase() === opName.toUpperCase());
                let totalAttHours = 0;

                opAttRecords.forEach(r => {
                    if (r.month_year && r.day && selectedDate) {
                        const recDateStr = `${r.month_year}-${String(r.day).padStart(2, '0')}`;
                        if (recDateStr === selectedDate) {
                            totalAttHours += parseFloat(r.hours || 0);
                        }
                    }
                });

                // Filter Prod Logs for this operator for selected date
                const opProdLogs = allProdLogs.filter(l => {
                    const lOp = (l.operator || '').trim().toUpperCase();
                    if (lOp !== opName.toUpperCase()) return false;
                    return l.date === selectedDate;
                });

                const sumRuntime = opProdLogs.reduce((sum, l) => sum + (parseFloat(l.runtime) || 0), 0);
                const sumIdleTime = opProdLogs.reduce((sum, l) => sum + (parseFloat(l.idle_hours) || 0) + (parseFloat(l.idle_hours_2) || 0) + (parseFloat(l.idle_hours_3) || 0), 0);
                const sumTargetQty = opProdLogs.reduce((sum, l) => sum + (parseFloat(l.target_qty) || 0), 0);
                const sumProdQty = opProdLogs.reduce((sum, l) => sum + (parseFloat(l.prod_qty) || 0), 0);

                // Multiple M/C value
                let multMcVal = '-';
                if (opProdLogs.length > 0) {
                    const multVals = opProdLogs.map(l => parseInt(l.multiple_mc) || 1);
                    const maxMult = Math.max(...multVals);
                    multMcVal = maxMult > 0 ? maxMult : 1;
                }

                let effPct = 0;
                if (sumTargetQty > 0) {
                    effPct = (sumProdQty / sumTargetQty) * 100;
                } else if (opProdLogs.length > 0) {
                    const validEffs = opProdLogs.map(l => parseFloat(l.efficiency) || 0).filter(e => e > 0);
                    if (validEffs.length > 0) {
                        effPct = validEffs.reduce((s, e) => s + e, 0) / validEffs.length;
                    }
                }

                const displayAttHours = totalAttHours.toFixed(2);

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${opName}</strong></td>
                    <td>${displayAttHours}</td>
                    <td>${sumRuntime.toFixed(2)}</td>
                    <td>${sumIdleTime.toFixed(2)}</td>
                    <td>${Math.round(sumTargetQty)}</td>
                    <td><strong>${Math.round(sumProdQty)}</strong></td>
                    <td>${multMcVal}</td>
                    <td><span style="font-weight:bold; color: ${effPct >= 80 ? '#16a34a' : (effPct >= 50 ? '#d97706' : '#ef4444')};">${effPct.toFixed(2)}%</span></td>
                `;
                tbody.appendChild(tr);
            });

            if (tbody.children.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">No data for selected date.</td></tr>';
            }
        } catch (err) {
            console.error('Error generating Operator Efficiency Report:', err);
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:#ef4444;">Error generating report.</td></tr>';
        }
    }

    document.getElementById('generateOperEffBtn')?.addEventListener('click', fetchOperEffReport);
    document.getElementById('exportOperEffBtn')?.addEventListener('click', () => {
        const table = document.getElementById('operEffTable');
        if (!table) return;
        const wb = XLSX.utils.table_to_book(table, { sheet: "Operator Efficiency" });
        XLSX.writeFile(wb, `Operator_Efficiency_Report_${new Date().toISOString().slice(0, 10)}.xlsx`);
    });

    // ====== INSERT MASTER CRUD ======
    const insertMasterModal = document.getElementById('insertMasterModal');
    const insertMasterForm = document.getElementById('insertMasterForm');
    const addInsertMasterBtn = document.getElementById('addInsertMasterBtn');
    const cancelInsertMasterBtn = document.getElementById('cancelInsertMasterBtn');
    const closeInsertMasterModalBtn = document.getElementById('closeInsertMasterModalBtn');

    async function fetchInsertMasters() {
        try {
            const res = await fetch('/api/insert_masters');
            const data = await res.json();
            renderInsertMasters(data);
        } catch (err) { console.error(err); }
    }

    function renderInsertMasters(inserts) {
        const tbody = document.getElementById('insertMasterBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!inserts || inserts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 0.75rem;">No insert records found. Click "+ Add Insert" or "Import Excel" to add records.</td></tr>';
            return;
        }
        const sorted = [...inserts].sort((a, b) => {
            const specA = (a.insert_spec || a.name || '').trim().toLowerCase();
            const specB = (b.insert_spec || b.name || '').trim().toLowerCase();
            return specA.localeCompare(specB, undefined, { numeric: true, sensitivity: 'base' });
        });
        sorted.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.id}</td>
                <td><strong>${item.insert_spec || item.name || ''}</strong></td>
                <td>${item.no_of_edges || 1}</td>
                <td class="actions-cell">
                    <button class="btn btn-outline edit-insert-btn" data-id="${item.id}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem;">Edit</button>
                    <button class="btn btn-outline delete-insert-btn" data-id="${item.id}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem; color: #ef4444; border-color: #ef4444;">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        tbody.querySelectorAll('.edit-insert-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.target.getAttribute('data-id');
                const res = await fetch('/api/insert_masters');
                const data = await res.json();
                const item = data.find(x => x.id == id);
                if (item) openInsertMasterModal(item);
            });
        });

        tbody.querySelectorAll('.delete-insert-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                if (confirm('Delete this insert master record?')) {
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/insert_masters/${id}`, { method: 'DELETE' });
                        if (res.ok) fetchInsertMasters();
                        else alert('Error deleting insert record');
                    } catch (err) { console.error(err); }
                }
            });
        });
    }

    function openInsertMasterModal(item = null) {
        if (!insertMasterModal) return;
        if (item) {
            document.getElementById('insertMasterModalTitle').textContent = 'Edit Insert Master';
            document.getElementById('insertMasterId').value = item.id;
            document.getElementById('insertSpecInput').value = item.insert_spec || item.name || '';
            document.getElementById('insertEdgesInput').value = item.no_of_edges || 1;
        } else {
            document.getElementById('insertMasterModalTitle').textContent = 'Add Insert Master';
            insertMasterForm.reset();
            document.getElementById('insertMasterId').value = '';
        }
        insertMasterModal.classList.add('show');
    }

    if (addInsertMasterBtn) addInsertMasterBtn.addEventListener('click', () => openInsertMasterModal());
    if (cancelInsertMasterBtn) cancelInsertMasterBtn.addEventListener('click', () => insertMasterModal.classList.remove('show'));
    if (closeInsertMasterModalBtn) closeInsertMasterModalBtn.addEventListener('click', () => insertMasterModal.classList.remove('show'));

    document.getElementById('importInsertMasterBtn')?.addEventListener('click', () => {
        document.getElementById('importInsertMasterInput')?.click();
    });

    const importInsertMasterInput = document.getElementById('importInsertMasterInput');
    if (importInsertMasterInput) {
        importInsertMasterInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = async (evt) => {
                try {
                    const data = evt.target.result;
                    const workbook = XLSX.read(data, { type: 'binary' });
                    const firstSheetName = workbook.SheetNames[0];
                    const worksheet = workbook.Sheets[firstSheetName];
                    const json = XLSX.utils.sheet_to_json(worksheet);

                    if (!json || json.length === 0) {
                        alert('No valid data found in Excel sheet.');
                        return;
                    }

                    const inserts = [];
                    json.forEach(row => {
                        let specVal = '';
                        let edgesVal = 1;

                        for (const key of Object.keys(row)) {
                            const k = key.trim().toLowerCase();
                            if (['insert spec', 'insert_spec', 'specification', 'insert name', 'spec', 'name'].includes(k)) {
                                specVal = String(row[key] || '').trim();
                            }
                            if (['no. of edges', 'no of edges', 'no_of_edges', 'edges', 'edge'].includes(k)) {
                                edgesVal = parseInt(row[key]) || 1;
                            }
                        }

                        if (specVal) {
                            inserts.push({
                                insert_spec: specVal,
                                no_of_edges: edgesVal,
                                grade: '',
                                make: '',
                                stock: 0,
                                price: 0.0
                            });
                        }
                    });

                    if (inserts.length === 0) {
                        alert('No valid insert spec rows found in Excel sheet. Make sure headers are "Insert Spec" and "No. of Edges".');
                        return;
                    }

                    const res = await fetch('/api/insert_masters/bulk', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ inserts })
                    });

                    if (res.ok) {
                        alert(`Successfully imported ${inserts.length} Insert Master records!`);
                        fetchInsertMasters();
                    } else {
                        alert('Error importing Excel data.');
                    }
                } catch (err) {
                    console.error('Error importing Insert Master Excel:', err);
                    alert('Error reading Excel file.');
                } finally {
                    importInsertMasterInput.value = '';
                }
            };
            reader.readAsBinaryString(file);
        });
    }

    if (insertMasterForm) {
        insertMasterForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('insertMasterId').value;
            const payload = {
                insert_spec: document.getElementById('insertSpecInput').value.trim(),
                no_of_edges: parseInt(document.getElementById('insertEdgesInput').value) || 1,
                grade: '',
                make: '',
                stock: 0,
                price: 0.00
            };
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/insert_masters/${id}` : '/api/insert_masters';

            try {
                const res = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    insertMasterModal.classList.remove('show');
                    fetchInsertMasters();
                } else {
                    alert('Error saving insert record');
                }
            } catch (err) { console.error(err); alert('Error saving insert record'); }
        });
    }

    // ====== DRILL MASTER CRUD ======
    const drillMasterModal = document.getElementById('drillMasterModal');
    const drillMasterForm = document.getElementById('drillMasterForm');
    const addDrillMasterBtn = document.getElementById('addDrillMasterBtn');
    const cancelDrillMasterBtn = document.getElementById('cancelDrillMasterBtn');
    const closeDrillMasterModalBtn = document.getElementById('closeDrillMasterModalBtn');

    async function fetchDrillMasters() {
        try {
            const res = await fetch('/api/drill_masters');
            const data = await res.json();
            renderDrillMasters(data);
        } catch (err) { console.error(err); }
    }

    function renderDrillMasters(drills) {
        const tbody = document.getElementById('drillMasterBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!drills || drills.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 0.75rem;">No drill records found. Click "+ Add Drill" or "Import Excel" to add records.</td></tr>';
            return;
        }
        drills.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.id}</td>
                <td><strong>${item.drill_size || item.size_dia || item.name || ''}</strong></td>
                <td>${item.sl_no || ''}</td>
                <td>${item.resharp_count || 0}</td>
                <td class="actions-cell">
                    <button class="btn btn-outline edit-drill-btn" data-id="${item.id}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem;">Edit</button>
                    <button class="btn btn-outline delete-drill-btn" data-id="${item.id}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem; color: #ef4444; border-color: #ef4444;">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        tbody.querySelectorAll('.edit-drill-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.target.getAttribute('data-id');
                const res = await fetch('/api/drill_masters');
                const data = await res.json();
                const item = data.find(x => x.id == id);
                if (item) openDrillMasterModal(item);
            });
        });

        tbody.querySelectorAll('.delete-drill-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                if (confirm('Delete this drill master record?')) {
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/drill_masters/${id}`, { method: 'DELETE' });
                        if (res.ok) fetchDrillMasters();
                        else alert('Error deleting drill record');
                    } catch (err) { console.error(err); }
                }
            });
        });
    }

    function openDrillMasterModal(item = null) {
        if (!drillMasterModal) return;
        if (item) {
            document.getElementById('drillMasterModalTitle').textContent = 'Edit Drill Master';
            document.getElementById('drillMasterId').value = item.id;
            document.getElementById('drillSizeInput').value = item.drill_size || item.size_dia || item.name || '';
            document.getElementById('drillSlNoInput').value = item.sl_no || '';
            document.getElementById('drillResharpInput').value = item.resharp_count || 0;
        } else {
            document.getElementById('drillMasterModalTitle').textContent = 'Add Drill Master';
            drillMasterForm.reset();
            document.getElementById('drillMasterId').value = '';
        }
        drillMasterModal.classList.add('show');
    }

    if (addDrillMasterBtn) addDrillMasterBtn.addEventListener('click', () => openDrillMasterModal());
    if (cancelDrillMasterBtn) cancelDrillMasterBtn.addEventListener('click', () => drillMasterModal.classList.remove('show'));
    if (closeDrillMasterModalBtn) closeDrillMasterModalBtn.addEventListener('click', () => drillMasterModal.classList.remove('show'));

    document.getElementById('importDrillMasterBtn')?.addEventListener('click', () => {
        document.getElementById('importDrillMasterInput')?.click();
    });

    const importDrillMasterInput = document.getElementById('importDrillMasterInput');
    if (importDrillMasterInput) {
        importDrillMasterInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = async (evt) => {
                try {
                    const data = evt.target.result;
                    const workbook = XLSX.read(data, { type: 'binary' });
                    const firstSheetName = workbook.SheetNames[0];
                    const worksheet = workbook.Sheets[firstSheetName];
                    const json = XLSX.utils.sheet_to_json(worksheet);

                    if (!json || json.length === 0) {
                        alert('No valid data found in Excel sheet.');
                        return;
                    }

                    const drills = [];
                    json.forEach(row => {
                        let sizeVal = '';
                        let slNoVal = '';
                        let resharpVal = 0;

                        for (const key of Object.keys(row)) {
                            const k = key.trim().toLowerCase();
                            if (['drill size', 'drill_size', 'size / dia', 'size', 'dia', 'drill name', 'name'].includes(k)) {
                                sizeVal = String(row[key] || '').trim();
                            }
                            if (['sl no', 'sl_no', 'serial no', 'sl.no', 'slno', 'serial'].includes(k)) {
                                slNoVal = String(row[key] || '').trim();
                            }
                            if (['resharp count', 'resharp_count', 'resharp', 'resharpen count', 'resharpening'].includes(k)) {
                                resharpVal = parseInt(row[key]) || 0;
                            }
                        }

                        if (sizeVal || slNoVal) {
                            drills.push({
                                drill_size: sizeVal,
                                sl_no: slNoVal,
                                resharp_count: resharpVal,
                                name: '',
                                size_dia: '',
                                specification: '',
                                make: '',
                                stock: 0,
                                price: 0.0
                            });
                        }
                    });

                    if (drills.length === 0) {
                        alert('No valid drill records found in Excel sheet. Make sure headers are "Drill Size", "Sl No", and "Resharp Count".');
                        return;
                    }

                    const res = await fetch('/api/drill_masters/bulk', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ drills })
                    });

                    if (res.ok) {
                        alert(`Successfully imported ${drills.length} Drill Master records!`);
                        fetchDrillMasters();
                    } else {
                        alert('Error importing Excel data.');
                    }
                } catch (err) {
                    console.error('Error importing Drill Master Excel:', err);
                    alert('Error reading Excel file.');
                } finally {
                    importDrillMasterInput.value = '';
                }
            };
            reader.readAsBinaryString(file);
        });
    }

    if (drillMasterForm) {
        drillMasterForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('drillMasterId').value;
            const payload = {
                drill_size: document.getElementById('drillSizeInput').value.trim(),
                sl_no: document.getElementById('drillSlNoInput').value.trim(),
                resharp_count: parseInt(document.getElementById('drillResharpInput').value) || 0,
                name: '',
                size_dia: '',
                specification: '',
                make: '',
                stock: 0,
                price: 0.00
            };
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/drill_masters/${id}` : '/api/drill_masters';

            try {
                const res = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    drillMasterModal.classList.remove('show');
                    fetchDrillMasters();
                } else {
                    alert('Error saving drill record');
                }
            } catch (err) { console.error(err); alert('Error saving drill record'); }
        });
    }

    // ====== INSERT RECEIPT CRUD ======
    const insertReceiptModal = document.getElementById('insertReceiptModal');
    const insertReceiptForm = document.getElementById('insertReceiptForm');
    const addInsertReceiptBtn = document.getElementById('addInsertReceiptBtn');
    const cancelInsertReceiptBtn = document.getElementById('cancelInsertReceiptBtn');
    const closeInsertReceiptModalBtn = document.getElementById('closeInsertReceiptModalBtn');

    async function fetchInsertReceipts() {
        try {
            const res = await fetch('/api/insert_receipts');
            const data = await res.json();
            renderInsertReceipts(data);
        } catch (err) { console.error(err); }
    }

    function renderInsertReceipts(receipts) {
        const tbody = document.getElementById('insertReceiptBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!receipts || receipts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 0.75rem;">No insert receipts found. Click "+ Add Receipt" or "Import Excel" to add records.</td></tr>';
            return;
        }
        receipts.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.id}</td>
                <td><span style="font-weight: 500;">${item.date || ''}</span></td>
                <td>${item.supplier || ''}</td>
                <td><strong>${item.insert_spec || ''}</strong></td>
                <td>${item.batch_no || ''}</td>
                <td>${item.qty || 0}</td>
                <td>Rs. ${(item.rate || 0).toFixed(2)}</td>
                <td class="actions-cell">
                    <button class="btn btn-outline edit-receipt-btn" data-id="${item.id}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem;">Edit</button>
                    <button class="btn btn-outline delete-receipt-btn" data-id="${item.id}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem; color: #ef4444; border-color: #ef4444;">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        tbody.querySelectorAll('.edit-receipt-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.target.getAttribute('data-id');
                const res = await fetch('/api/insert_receipts');
                const data = await res.json();
                const item = data.find(x => x.id == id);
                if (item) openInsertReceiptModal(item);
            });
        });

        tbody.querySelectorAll('.delete-receipt-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                if (confirm('Delete this insert receipt record?')) {
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/insert_receipts/${id}`, { method: 'DELETE' });
                        if (res.ok) fetchInsertReceipts();
                        else alert('Error deleting receipt record');
                    } catch (err) { console.error(err); }
                }
            });
        });
    }

    // Reusable Searchable Select helper using TomSelect
    const tomSelectCache = {};

    function makeSearchableSelect(selectId, placeholderText = '-- Select Insert Spec --') {
        const select = typeof selectId === 'string' ? document.getElementById(selectId) : selectId;
        if (!select) return;
        const id = select.id || 'select_' + Math.random().toString(36).substr(2, 5);

        if (tomSelectCache[id]) {
            try { tomSelectCache[id].destroy(); } catch(e) {}
            delete tomSelectCache[id];
        }

        const oldWrapper = select.parentElement ? select.parentElement.querySelector('.searchable-select-wrapper') : null;
        if (oldWrapper) {
            oldWrapper.remove();
            select.style.display = 'block';
        }

        try {
            if (window.TomSelect) {
                tomSelectCache[id] = new TomSelect(select, {
                    create: false,
                    placeholder: placeholderText,
                    allowEmptyOption: true,
                    maxOptions: 500,
                    sortField: { field: "text", direction: "asc" }
                });
            }
        } catch (e) {
            console.error('Error initializing TomSelect on ' + id, e);
        }
    }

    async function populateInsertSpecDropdown(selectedSpec = '') {
        const sel = document.getElementById('receiptInsertSpecSelect');
        if (!sel) return;
        sel.innerHTML = '<option value="">-- Select Insert Spec --</option>';
        try {
            const res = await fetch('/api/insert_masters');
            const data = await res.json();
            data.forEach(item => {
                const spec = item.insert_spec || item.name || '';
                if (spec) {
                    const opt = document.createElement('option');
                    opt.value = spec;
                    opt.textContent = spec;
                    if (selectedSpec && selectedSpec.trim().toLowerCase() === spec.trim().toLowerCase()) {
                        opt.selected = true;
                    }
                    sel.appendChild(opt);
                }
            });
            makeSearchableSelect('receiptInsertSpecSelect');
        } catch (e) { console.error('Error fetching insert specs for dropdown:', e); }
    }

    async function generateNextBatchNo(dateStr) {
        if (!dateStr) {
            dateStr = new Date().toISOString().split('T')[0];
        }
        const parts = dateStr.split('-');
        let month = parseInt(parts[1], 10);
        let day = parseInt(parts[2], 10);
        if (isNaN(month) || isNaN(day)) {
            const d = new Date();
            month = d.getMonth() + 1;
            day = d.getDate();
        }
        const monthLetters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l'];
        const monthLetter = monthLetters[(month - 1) % 12] || 'a';
        const prefix = `${monthLetter}${day}`;

        try {
            const res = await fetch('/api/insert_receipts');
            const data = await res.json();
            let maxSerial = 0;

            if (Array.isArray(data)) {
                data.forEach(item => {
                    if (item.batch_no) {
                        const b = item.batch_no.trim().toLowerCase();
                        if (b.startsWith(prefix.toLowerCase())) {
                            const rest = b.substring(prefix.length);
                            const num = parseInt(rest, 10);
                            if (!isNaN(num) && num > maxSerial) {
                                maxSerial = num;
                            }
                        }
                    }
                });
            }
            return `${prefix}${maxSerial + 1}`;
        } catch (err) {
            console.error('Error generating batch no:', err);
            return `${prefix}1`;
        }
    }

    async function openInsertReceiptModal(item = null) {
        if (!insertReceiptModal) return;
        await populateInsertSpecDropdown(item ? item.insert_spec : '');
        if (item) {
            document.getElementById('insertReceiptModalTitle').textContent = 'Edit Insert Receipt';
            document.getElementById('insertReceiptId').value = item.id;
            document.getElementById('receiptDateInput').value = item.date || '';
            document.getElementById('receiptSupplierInput').value = item.supplier || '';
            document.getElementById('receiptBatchNoInput').value = item.batch_no || '';
            document.getElementById('receiptQtyInput').value = item.qty || 1;
            document.getElementById('receiptRateInput').value = item.rate || 0.00;
        } else {
            document.getElementById('insertReceiptModalTitle').textContent = 'Add Insert Receipt';
            insertReceiptForm.reset();
            document.getElementById('insertReceiptId').value = '';
            const todayStr = new Date().toISOString().split('T')[0];
            document.getElementById('receiptDateInput').value = todayStr;
            const autoBatch = await generateNextBatchNo(todayStr);
            document.getElementById('receiptBatchNoInput').value = autoBatch;
        }
        makeSearchableSelect('receiptInsertSpecSelect');
        insertReceiptModal.classList.add('show');
    }

    document.getElementById('receiptDateInput')?.addEventListener('change', async (e) => {
        const isEdit = !!document.getElementById('insertReceiptId').value;
        if (!isEdit && e.target.value) {
            const nextBatch = await generateNextBatchNo(e.target.value);
            document.getElementById('receiptBatchNoInput').value = nextBatch;
        }
    });

    if (addInsertReceiptBtn) addInsertReceiptBtn.addEventListener('click', () => openInsertReceiptModal());
    if (cancelInsertReceiptBtn) cancelInsertReceiptBtn.addEventListener('click', () => insertReceiptModal.classList.remove('show'));
    if (closeInsertReceiptModalBtn) closeInsertReceiptModalBtn.addEventListener('click', () => insertReceiptModal.classList.remove('show'));

    document.getElementById('importInsertReceiptBtn')?.addEventListener('click', () => {
        document.getElementById('importInsertReceiptInput')?.click();
    });

    const importInsertReceiptInput = document.getElementById('importInsertReceiptInput');
    if (importInsertReceiptInput) {
        importInsertReceiptInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = async (evt) => {
                try {
                    const data = evt.target.result;
                    const workbook = XLSX.read(data, { type: 'binary' });
                    const firstSheetName = workbook.SheetNames[0];
                    const worksheet = workbook.Sheets[firstSheetName];
                    const json = XLSX.utils.sheet_to_json(worksheet);

                    if (!json || json.length === 0) {
                        alert('No valid data found in Excel sheet.');
                        return;
                    }

                    const receipts = [];
                    const todayStr = new Date().toISOString().slice(0, 10);
                    json.forEach(row => {
                        let dateVal = todayStr;
                        let supplierVal = '';
                        let specVal = '';
                        let batchVal = '';
                        let qtyVal = 0;
                        let rateVal = 0.0;

                        for (const key of Object.keys(row)) {
                            const k = key.trim().toLowerCase();
                            if (['date', 'receipt date', 'receipt_date'].includes(k)) {
                                dateVal = String(row[key] || '').trim();
                            }
                            if (['supplier', 'vendor', 'supplier name'].includes(k)) {
                                supplierVal = String(row[key] || '').trim();
                            }
                            if (['insert spec', 'insert_spec', 'spec', 'specification', 'insert'].includes(k)) {
                                specVal = String(row[key] || '').trim();
                            }
                            if (['batch no', 'batch_no', 'batch', 'batch number', 'lot no'].includes(k)) {
                                batchVal = String(row[key] || '').trim();
                            }
                            if (['qty', 'quantity', 'count'].includes(k)) {
                                qtyVal = parseInt(row[key]) || 0;
                            }
                            if (['rate', 'price', 'rate (rs)', 'unit rate'].includes(k)) {
                                rateVal = parseFloat(row[key]) || 0.0;
                            }
                        }

                        if (specVal) {
                            receipts.push({
                                date: dateVal || todayStr,
                                supplier: supplierVal,
                                insert_spec: specVal,
                                batch_no: batchVal,
                                qty: qtyVal,
                                rate: rateVal
                            });
                        }
                    });

                    if (receipts.length === 0) {
                        alert('No valid receipt records found in Excel sheet. Make sure headers are "Date", "Supplier", "Insert Spec", "Batch No", "Qty", and "Rate".');
                        return;
                    }

                    const res = await fetch('/api/insert_receipts/bulk', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ receipts })
                    });

                    if (res.ok) {
                        alert(`Successfully imported ${receipts.length} Insert Receipt records!`);
                        fetchInsertReceipts();
                    } else {
                        alert('Error importing Excel data.');
                    }
                } catch (err) {
                    console.error('Error importing Insert Receipt Excel:', err);
                    alert('Error reading Excel file.');
                } finally {
                    importInsertReceiptInput.value = '';
                }
            };
            reader.readAsBinaryString(file);
        });
    }

    if (insertReceiptForm) {
        insertReceiptForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('insertReceiptId').value;
            const payload = {
                date: document.getElementById('receiptDateInput').value,
                supplier: document.getElementById('receiptSupplierInput').value.trim(),
                insert_spec: document.getElementById('receiptInsertSpecSelect').value,
                batch_no: document.getElementById('receiptBatchNoInput').value.trim(),
                qty: parseInt(document.getElementById('receiptQtyInput').value) || 0,
                rate: parseFloat(document.getElementById('receiptRateInput').value) || 0.00
            };
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/insert_receipts/${id}` : '/api/insert_receipts';

            try {
                const res = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    insertReceiptModal.classList.remove('show');
                    fetchInsertReceipts();
                } else {
                    alert('Error saving receipt record');
                }
            } catch (err) { console.error(err); alert('Error saving receipt record'); }
        });
    }

    // ====== INSERT ISSUE CRUD ======
    const insertIssueModal = document.getElementById('insertIssueModal');
    const insertIssueForm = document.getElementById('insertIssueForm');
    const addInsertIssueBtn = document.getElementById('addInsertIssueBtn');
    const cancelInsertIssueBtn = document.getElementById('cancelInsertIssueBtn');
    const closeInsertIssueModalBtn = document.getElementById('closeInsertIssueModalBtn');

    let allReceiptsCache = [];
    let allPartMastersCache = [];

    let allInsertMastersCache = [];

    async function fetchInsertIssues() {
        try {
            const [issueRes, masterRes] = await Promise.all([
                fetch('/api/insert_issues'),
                fetch('/api/insert_masters')
            ]);
            const data = await issueRes.json();
            allInsertMastersCache = await masterRes.json();
            renderInsertIssues(data);
        } catch (err) { console.error(err); }
    }

    function normalizeEdgeObj(rawEdgeData) {
        const result = {};
        if (!rawEdgeData) return result;
        let parsed = rawEdgeData;
        try {
            while (typeof parsed === 'string') {
                parsed = JSON.parse(parsed);
            }
        } catch(e) {}
        if (typeof parsed !== 'object' || parsed === null) return result;

        for (const key of Object.keys(parsed)) {
            const val = parsed[key];
            if (val !== undefined && val !== null && val !== '') {
                if (typeof val === 'object' && val.qty !== undefined) {
                    result[key] = {
                        qty: parseFloat(val.qty) || 0,
                        uIdx: val.uIdx !== undefined ? parseInt(val.uIdx) : 0,
                        partno: val.partno || ''
                    };
                } else if (!isNaN(val) && parseFloat(val) > 0) {
                    result[key] = {
                        qty: parseFloat(val),
                        uIdx: 0,
                        partno: ''
                    };
                }
            }
        }
        return result;
    }

    function renderInsertIssues(issues) {
        const tbody = document.getElementById('insertIssueBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!issues || issues.length === 0) {
            tbody.innerHTML = '<tr><td colspan="11" style="text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 0.75rem;">No insert issue records found. Click "+ Issue Insert" or "Import Excel" to add records.</td></tr>';
            return;
        }

        // Aggregate edge completion per group (insert_spec + batch_no)
        const groupEdgeMap = {}; // key: "insert_spec|batch_no" -> Set of filled edge numbers
        issues.forEach(item => {
            let numEdges = 4;
            const specKey = (item.insert_spec || '').trim().toLowerCase();
            const master = allInsertMastersCache.find(s => (s.insert_spec || s.name || '').trim().toLowerCase() === specKey);
            if (master) {
                numEdges = parseInt(master.no_of_edges) || parseInt(master.edges) || 4;
            }

            let isComplete = false;
            let filledCount = 0;

            if (item.edge_data) {
                try {
                    const normalized = normalizeEdgeObj(item.edge_data);
                    for (let i = 1; i <= numEdges; i++) {
                        const info = normalized[String(i)];
                        if (info && info.qty > 0) {
                            filledCount++;
                        }
                    }
                    if (filledCount >= numEdges && numEdges > 0) {
                        isComplete = true;
                    }
                } catch (e) { isComplete = false; }
            }

            let usages = [];
            if (item.usages) {
                try {
                    let parsed = item.usages;
                    while (typeof parsed === 'string') {
                        parsed = JSON.parse(parsed);
                    }
                    if (Array.isArray(parsed)) usages = parsed;
                } catch(e) {}
            }
            if (!usages || !Array.isArray(usages) || usages.length === 0) {
                usages = [{
                    machine: item.machine || '',
                    operator: item.operator || '',
                    partno: item.partno || '',
                    opn_no: item.opn_no || ''
                }];
            }

            const rowSpan = usages.length;

            usages.forEach((u, uIdx) => {
                const tr = document.createElement('tr');
                if (uIdx > 0) {
                    tr.style.background = '#f9fafb';
                }

                if (uIdx === 0) {
                    tr.innerHTML = `
                        <td rowspan="${rowSpan}" style="vertical-align: middle; font-weight: bold;">${item.id}</td>
                        <td rowspan="${rowSpan}" style="vertical-align: middle;"><span style="font-weight: 500;">${item.date || ''}</span></td>
                        <td rowspan="${rowSpan}" style="vertical-align: middle;">${item.department || ''}</td>
                        <td rowspan="${rowSpan}" style="vertical-align: middle;"><strong>${item.insert_spec || ''}</strong></td>
                        <td rowspan="${rowSpan}" style="vertical-align: middle;">${item.batch_no || ''}</td>
                        <td rowspan="${rowSpan}" style="vertical-align: middle;"><span style="font-weight: 600; color: var(--primary-color);">${item.qty_issued || 0}</span></td>
                        <td>${u.machine || ''}</td>
                        <td>${u.operator || ''}</td>
                        <td>${u.partno || ''}</td>
                        <td>${u.opn_no || ''}</td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <button class="btn btn-outline monitor-issue-btn" data-id="${item.id}" data-usage-idx="${uIdx}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem; color: #2563eb; border-color: #2563eb; font-weight: 600;">Insert Monitor</button>
                                ${isComplete ? '<span title="All edge details entered for this issue" style="display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; background-color: #22c55e; color: white; border-radius: 4px; font-size: 14px; font-weight: bold; box-shadow: 0 1px 3px rgba(0,0,0,0.15);">✓</span>' : ''}
                            </div>
                        </td>
                        <td class="actions-cell">
                            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                                <button class="btn btn-outline add-usage-btn" data-id="${item.id}" style="padding: 0.25rem 0.45rem; font-size: 0.78rem; color: #16a34a; border-color: #16a34a; font-weight: 600;" title="Add Usage Entry">+ Add Usage</button>
                                <button class="btn btn-outline edit-issue-btn" data-id="${item.id}" style="padding: 0.25rem 0.45rem; font-size: 0.78rem;">Edit</button>
                                <button class="btn btn-outline delete-issue-btn" data-id="${item.id}" style="padding: 0.25rem 0.45rem; font-size: 0.78rem; color: #ef4444; border-color: #ef4444;">Delete</button>
                            </div>
                        </td>
                    `;
                } else {
                    tr.innerHTML = `
                        <td>${u.machine || ''}</td>
                        <td>${u.operator || ''}</td>
                        <td>${u.partno || ''}</td>
                        <td>${u.opn_no || ''}</td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <button class="btn btn-outline monitor-issue-btn" data-id="${item.id}" data-usage-idx="${uIdx}" style="padding: 0.3rem 0.6rem; font-size: 0.85rem; color: #2563eb; border-color: #2563eb; font-weight: 600;">Insert Monitor</button>
                                ${isComplete ? '<span title="All edge details entered for this issue" style="display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; background-color: #22c55e; color: white; border-radius: 4px; font-size: 14px; font-weight: bold; box-shadow: 0 1px 3px rgba(0,0,0,0.15);">✓</span>' : ''}
                            </div>
                        </td>
                        <td class="actions-cell">
                            <button class="btn btn-outline delete-subusage-btn" data-id="${item.id}" data-usage-idx="${uIdx}" style="padding: 0.25rem 0.45rem; font-size: 0.78rem; color: #ef4444; border-color: #ef4444;" title="Remove this usage entry">Delete Usage</button>
                        </td>
                    `;
                }
                tbody.appendChild(tr);
            });
        });

        tbody.querySelectorAll('.add-usage-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.getAttribute('data-id');
                const res = await fetch('/api/insert_issues');
                const data = await res.json();
                const item = data.find(x => x.id == id);
                if (item) openAddUsageModal(item);
            });
        });

        tbody.querySelectorAll('.delete-subusage-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.getAttribute('data-id');
                const uIdx = parseInt(btn.getAttribute('data-usage-idx'));
                if (confirm('Delete this additional usage entry?')) {
                    try {
                        const res = await fetch('/api/insert_issues');
                        const data = await res.json();
                        const item = data.find(x => x.id == id);
                        if (!item) return;

                        let usages = [];
                        if (item.usages) {
                            try {
                                let parsed = item.usages;
                                while (typeof parsed === 'string') {
                                    parsed = JSON.parse(parsed);
                                }
                                if (Array.isArray(parsed)) usages = parsed;
                            } catch(e) {}
                        }
                        if (usages.length > uIdx) {
                            usages.splice(uIdx, 1);
                            const payload = {
                                date: item.date || '',
                                department: item.department || '',
                                insert_spec: item.insert_spec || '',
                                batch_no: item.batch_no || '',
                                qty_issued: item.qty_issued || 1,
                                machine: item.machine || '',
                                operator: item.operator || '',
                                partno: item.partno || '',
                                opn_no: item.opn_no || '',
                                usages: JSON.stringify(usages),
                                receipt_id: item.receipt_id || null,
                                edge_data: item.edge_data || ''
                            };
                            await fetch(`/api/insert_issues/${id}`, {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(payload)
                            });
                            fetchInsertIssues();
                        }
                    } catch(err) { console.error(err); }
                }
            });
        });

        tbody.querySelectorAll('.monitor-issue-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = btn.getAttribute('data-id');
                const uIdx = parseInt(btn.getAttribute('data-usage-idx')) || 0;
                const res = await fetch('/api/insert_issues');
                const data = await res.json();
                const item = data.find(x => x.id == id);
                if (item) openInsertMonitorModal(item, uIdx);
            });
        });

        tbody.querySelectorAll('.edit-issue-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.target.getAttribute('data-id');
                const res = await fetch('/api/insert_issues');
                const data = await res.json();
                const item = data.find(x => x.id == id);
                if (item) openInsertIssueModal(item);
            });
        });

        tbody.querySelectorAll('.delete-issue-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                if (confirm('Delete this insert issue record? This will restore the stock back to the receipt batch.')) {
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/insert_issues/${id}`, { method: 'DELETE' });
                        if (res.ok) fetchInsertIssues();
                        else alert('Error deleting issue record');
                    } catch (err) { console.error(err); }
                }
            });
        });
    }

    let allMachinesCache = [];
    let allOperatorsCache = [];

    async function populateIssueModalDropdowns(selectedDept = '', selectedSpec = '', selectedBatch = '', selectedPart = '', selectedOpn = '') {
        const deptSel = document.getElementById('issueDeptSelect');
        const specSel = document.getElementById('issueInsertSpecSelect');

        // 1. Departments
        deptSel.innerHTML = '<option value="">-- Select Dept --</option>';
        try {
            const dRes = await fetch('/api/departments');
            const depts = await dRes.json();
            depts.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.name;
                opt.textContent = d.name;
                if (selectedDept && selectedDept.trim().toUpperCase() === d.name.trim().toUpperCase()) {
                    opt.selected = true;
                }
                deptSel.appendChild(opt);
            });
        } catch (e) { console.error(e); }

        // Fetch dependency caches
        try {
            const [mRes, oRes, pRes] = await Promise.all([
                fetch('/api/machines'),
                fetch('/api/operators'),
                fetch('/api/partmaster')
            ]);
            allMachinesCache = await mRes.json();
            allOperatorsCache = await oRes.json();
            allPartMastersCache = await pRes.json();
        } catch (e) { console.error(e); }

        // 2. Insert Specs
        specSel.innerHTML = '<option value="">-- Select Insert Spec --</option>';
        try {
            const specRes = await fetch('/api/insert_masters');
            const specs = await specRes.json();
            specs.forEach(s => {
                const sp = s.insert_spec || s.name || '';
                if (sp) {
                    const opt = document.createElement('option');
                    opt.value = sp;
                    opt.textContent = sp;
                    if (selectedSpec && selectedSpec.trim().toLowerCase() === sp.trim().toLowerCase()) {
                        opt.selected = true;
                    }
                    specSel.appendChild(opt);
                }
            });
            makeSearchableSelect('issueInsertSpecSelect');
        } catch (e) { console.error(e); }

        filterIssueDropdownsByDept(selectedDept, selectedPart);

        if (selectedSpec) {
            await updateBatchDropdownForSpec(selectedSpec, selectedBatch);
        }
        if (selectedPart) {
            await updateOpnDropdownForPart(selectedPart, selectedOpn);
        }
    }

    // ====== ADD USAGE MODAL LOGIC ======
    const addUsageModal = document.getElementById('addUsageModal');
    const closeAddUsageModalBtn = document.getElementById('closeAddUsageModalBtn');
    const cancelAddUsageBtn = document.getElementById('cancelAddUsageBtn');
    const addUsageForm = document.getElementById('addUsageForm');
    let currentAddUsageItem = null;

    if (closeAddUsageModalBtn) closeAddUsageModalBtn.addEventListener('click', () => addUsageModal.classList.remove('show'));
    if (cancelAddUsageBtn) cancelAddUsageBtn.addEventListener('click', () => addUsageModal.classList.remove('show'));

    async function openAddUsageModal(item) {
        if (!addUsageModal || !item) return;
        currentAddUsageItem = item;
        document.getElementById('addUsageIssueId').value = item.id;
        document.getElementById('addUsageSubtitle').textContent = `ID #${item.id} | ${item.insert_spec || ''} (Batch: ${item.batch_no || '-'})`;

        // Ensure dependency caches are populated
        if (allMachinesCache.length === 0 || allOperatorsCache.length === 0 || allPartMastersCache.length === 0) {
            try {
                const [mRes, oRes, pRes] = await Promise.all([
                    fetch('/api/machines'),
                    fetch('/api/operators'),
                    fetch('/api/partmaster')
                ]);
                allMachinesCache = await mRes.json();
                allOperatorsCache = await oRes.json();
                allPartMastersCache = await pRes.json();
            } catch (e) { console.error(e); }
        }

        const machSel = document.getElementById('addUsageMachineSelect');
        const opSel = document.getElementById('addUsageOperatorSelect');
        const partSel = document.getElementById('addUsagePartNoSelect');
        const opnSel = document.getElementById('addUsageOpnNoSelect');

        const cleanDept = (item.department || '').trim().toUpperCase();

        machSel.innerHTML = '<option value="">-- Select Machine --</option>';
        const filteredMachines = cleanDept ? allMachinesCache.filter(m => (m.department || '').trim().toUpperCase() === cleanDept) : allMachinesCache;
        const machinesToDisplay = filteredMachines.length > 0 ? filteredMachines : allMachinesCache;
        machinesToDisplay.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.name;
            opt.textContent = m.name;
            machSel.appendChild(opt);
        });

        opSel.innerHTML = '<option value="">-- Select Operator --</option>';
        const filteredOperators = cleanDept ? allOperatorsCache.filter(o => (o.department || '').trim().toUpperCase() === cleanDept) : allOperatorsCache;
        const operatorsToDisplay = filteredOperators.length > 0 ? filteredOperators : allOperatorsCache;
        operatorsToDisplay.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        operatorsToDisplay.forEach(o => {
            const opt = document.createElement('option');
            opt.value = o.name;
            opt.textContent = o.name;
            opSel.appendChild(opt);
        });

        partSel.innerHTML = '<option value="">-- Select Part No --</option>';
        const filteredParts = cleanDept ? allPartMastersCache.filter(p => (p.department || '').trim().toUpperCase() === cleanDept) : allPartMastersCache;
        const partsToDisplay = filteredParts.length > 0 ? filteredParts : allPartMastersCache;
        partsToDisplay.forEach(p => {
            if (p.partno) {
                const opt = document.createElement('option');
                opt.value = p.partno;
                opt.textContent = p.partno;
                partSel.appendChild(opt);
            }
        });

        opnSel.innerHTML = '<option value="">-- Select Operation --</option>';
        addUsageModal.classList.add('show');
    }

    document.getElementById('addUsagePartNoSelect')?.addEventListener('change', async (e) => {
        const opnSel = document.getElementById('addUsageOpnNoSelect');
        opnSel.innerHTML = '<option value="">-- Select Operation --</option>';
        const partVal = e.target.value;
        if (!partVal) return;

        const partObj = allPartMastersCache.find(p => (p.partno || '').trim().toUpperCase() === partVal.trim().toUpperCase());
        if (!partObj) return;

        try {
            const res = await fetch(`/api/partmaster/${partObj.id}/operations`);
            const ops = await res.json();
            ops.sort((a, b) => (parseInt(a.opn_no) || 0) - (parseInt(b.opn_no) || 0));
            ops.forEach(o => {
                const opt = document.createElement('option');
                opt.value = o.opn_no;
                opt.textContent = `${o.opn_no} - ${o.description || ''}`;
                opnSel.appendChild(opt);
            });
        } catch (err) { console.error(err); }
    });

    if (addUsageForm) {
        addUsageForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('addUsageIssueId').value;
            if (!id) return;

            const mach = document.getElementById('addUsageMachineSelect').value;
            const op = document.getElementById('addUsageOperatorSelect').value;
            const part = document.getElementById('addUsagePartNoSelect').value;
            const opn = document.getElementById('addUsageOpnNoSelect').value;

            try {
                const getRes = await fetch(`/api/insert_issues/${id}`);
                if (!getRes.ok) {
                    alert('Error fetching issue record');
                    return;
                }
                const currentItem = await getRes.json();

                let usages = [];
                if (currentItem.usages) {
                    try {
                        let parsed = currentItem.usages;
                        while (typeof parsed === 'string') {
                            parsed = JSON.parse(parsed);
                        }
                        if (Array.isArray(parsed)) usages = parsed;
                    } catch(e) {}
                }
                if (!usages || !Array.isArray(usages) || usages.length === 0) {
                    usages = [{
                        machine: currentItem.machine || '',
                        operator: currentItem.operator || '',
                        partno: currentItem.partno || '',
                        opn_no: currentItem.opn_no || ''
                    }];
                }

                usages.push({ machine: mach, operator: op, partno: part, opn_no: opn });

                const payload = {
                    date: currentItem.date || '',
                    department: currentItem.department || '',
                    insert_spec: currentItem.insert_spec || '',
                    batch_no: currentItem.batch_no || '',
                    qty_issued: currentItem.qty_issued || 1,
                    machine: currentItem.machine || '',
                    operator: currentItem.operator || '',
                    partno: currentItem.partno || '',
                    opn_no: currentItem.opn_no || '',
                    usages: JSON.stringify(usages),
                    receipt_id: currentItem.receipt_id || null,
                    edge_data: currentItem.edge_data || ''
                };

                const res = await fetch(`/api/insert_issues/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    addUsageModal.classList.remove('show');
                    addUsageForm.reset();
                    fetchInsertIssues();
                } else {
                    const errTxt = await res.text();
                    console.error('Error adding usage:', errTxt);
                    alert('Error adding usage entry');
                }
            } catch(err) { console.error(err); alert('Error adding usage entry'); }
        });
    }

    function createUsageCard(usageData = null) {
        const container = document.getElementById('usageEntriesContainer');
        if (!container) return;

        const cardIndex = container.children.length + 1;
        const card = document.createElement('div');
        card.className = 'usage-entry-card';
        card.style.cssText = 'background: rgba(0,0,0,0.02); border: 1px solid var(--border-color, #cbd5e1); border-radius: 8px; padding: 0.8rem; position: relative; margin-bottom: 0.4rem;';

        const cleanDept = (document.getElementById('issueDeptSelect')?.value || '').trim().toUpperCase();

        const filteredMachines = cleanDept ? allMachinesCache.filter(m => (m.department || '').trim().toUpperCase() === cleanDept) : allMachinesCache;
        const machinesToDisplay = filteredMachines.length > 0 ? filteredMachines : allMachinesCache;
        let machineOpts = '<option value="">-- Select Machine --</option>';
        machinesToDisplay.forEach(m => {
            const sel = (usageData && usageData.machine === m.name) ? 'selected' : '';
            machineOpts += `<option value="${m.name}" ${sel}>${m.name}</option>`;
        });

        const filteredOperators = cleanDept ? allOperatorsCache.filter(o => (o.department || '').trim().toUpperCase() === cleanDept) : allOperatorsCache;
        const operatorsToDisplay = filteredOperators.length > 0 ? filteredOperators : allOperatorsCache;
        operatorsToDisplay.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        let operatorOpts = '<option value="">-- Select Operator --</option>';
        operatorsToDisplay.forEach(o => {
            const sel = (usageData && usageData.operator === o.name) ? 'selected' : '';
            operatorOpts += `<option value="${o.name}" ${sel}>${o.name}</option>`;
        });

        const filteredParts = cleanDept ? allPartMastersCache.filter(p => (p.department || '').trim().toUpperCase() === cleanDept) : allPartMastersCache;
        const partsToDisplay = filteredParts.length > 0 ? filteredParts : allPartMastersCache;
        let partOpts = '<option value="">-- Select Part No --</option>';
        partsToDisplay.forEach(p => {
            if (p.partno) {
                const sel = (usageData && usageData.partno === p.partno) ? 'selected' : '';
                partOpts += `<option value="${p.partno}" ${sel}>${p.partno}</option>`;
            }
        });

        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                <span style="font-weight: 600; font-size: 0.8rem; color: var(--text-muted);">Usage Entry #${cardIndex}</span>
                ${cardIndex > 1 ? '<button type="button" class="remove-usage-card-btn" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 1.1rem; font-weight: bold;" title="Remove Entry">&times;</button>' : ''}
            </div>
            <div class="form-row" style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="flex: 1;">
                    <label style="font-size: 0.8rem; font-weight: 600; display: block; margin-bottom: 0.2rem;">Machine</label>
                    <select class="usage-machine-select" style="width: 100%; padding: 0.4rem; border: 1px solid var(--border-color); border-radius: 6px; font-size: 0.85rem;">
                        ${machineOpts}
                    </select>
                </div>
                <div style="flex: 1;">
                    <label style="font-size: 0.8rem; font-weight: 600; display: block; margin-bottom: 0.2rem;">Operator</label>
                    <select class="usage-operator-select" style="width: 100%; padding: 0.4rem; border: 1px solid var(--border-color); border-radius: 6px; font-size: 0.85rem;">
                        ${operatorOpts}
                    </select>
                </div>
            </div>
            <div class="form-row" style="display: flex; gap: 0.5rem;">
                <div style="flex: 1;">
                    <label style="font-size: 0.8rem; font-weight: 600; display: block; margin-bottom: 0.2rem;">Part No</label>
                    <select class="usage-partno-select" style="width: 100%; padding: 0.4rem; border: 1px solid var(--border-color); border-radius: 6px; font-size: 0.85rem;">
                        ${partOpts}
                    </select>
                </div>
                <div style="flex: 1;">
                    <label style="font-size: 0.8rem; font-weight: 600; display: block; margin-bottom: 0.2rem;">Opn No</label>
                    <select class="usage-opnno-select" style="width: 100%; padding: 0.4rem; border: 1px solid var(--border-color); border-radius: 6px; font-size: 0.85rem;">
                        <option value="">-- Select Opn --</option>
                    </select>
                </div>
            </div>
        `;

        container.appendChild(card);

        const removeBtn = card.querySelector('.remove-usage-card-btn');
        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                card.remove();
                container.querySelectorAll('.usage-entry-card').forEach((c, idx) => {
                    const label = c.querySelector('span');
                    if (label) label.textContent = `Usage Entry #${idx + 1}`;
                });
            });
        }

        const partSel = card.querySelector('.usage-partno-select');
        const opnSel = card.querySelector('.usage-opnno-select');

        partSel.addEventListener('change', async (e) => {
            const selectedPart = e.target.value;
            opnSel.innerHTML = '<option value="">-- Select Opn --</option>';
            if (!selectedPart) return;

            const partObj = allPartMastersCache.find(p => (p.partno || '').trim().toUpperCase() === selectedPart.trim().toUpperCase());
            if (!partObj) return;

            try {
                const res = await fetch(`/api/partmaster/${partObj.id}/operations`);
                const ops = await res.json();
                ops.sort((a, b) => (parseInt(a.opn_no) || 0) - (parseInt(b.opn_no) || 0));
                ops.forEach(o => {
                    const opt = document.createElement('option');
                    opt.value = o.opn_no;
                    opt.textContent = `${o.opn_no} - ${o.description || ''}`;
                    if (usageData && usageData.opn_no && usageData.opn_no.trim().toLowerCase() === o.opn_no.trim().toLowerCase()) {
                        opt.selected = true;
                    }
                    opnSel.appendChild(opt);
                });
            } catch (err) { console.error(err); }
        });

        if (usageData && usageData.partno) {
            partSel.dispatchEvent(new Event('change'));
        }
    }

    document.getElementById('addUsageEntryRowBtn')?.addEventListener('click', () => createUsageCard());

    function filterIssueDropdownsByDept(dept = '', selectedPart = '') {
        const machSel = document.getElementById('issueMachineSelect');
        const opSel = document.getElementById('issueOperatorSelect');
        const partSel = document.getElementById('issuePartNoSelect');

        const cleanDept = (dept || '').trim().toUpperCase();

        // 1. Filter Machines
        if (machSel) {
            machSel.innerHTML = '<option value="">-- Select Machine --</option>';
            const filteredMachines = cleanDept ? allMachinesCache.filter(m => (m.department || '').trim().toUpperCase() === cleanDept) : allMachinesCache;
            const machinesToDisplay = filteredMachines.length > 0 ? filteredMachines : allMachinesCache;
            machinesToDisplay.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.name;
                opt.textContent = m.name;
                machSel.appendChild(opt);
            });
        }

        // 2. Filter Operators
        if (opSel) {
            opSel.innerHTML = '<option value="">-- Select Operator --</option>';
            const filteredOperators = cleanDept ? allOperatorsCache.filter(o => (o.department || '').trim().toUpperCase() === cleanDept) : allOperatorsCache;
            const operatorsToDisplay = filteredOperators.length > 0 ? filteredOperators : allOperatorsCache;
            operatorsToDisplay.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
            operatorsToDisplay.forEach(o => {
                const opt = document.createElement('option');
                opt.value = o.name;
                opt.textContent = o.name;
                opSel.appendChild(opt);
            });
        }

        // 3. Filter Parts
        if (partSel) {
            partSel.innerHTML = '<option value="">-- Select Part No --</option>';
            const filteredParts = cleanDept ? allPartMastersCache.filter(p => (p.department || '').trim().toUpperCase() === cleanDept) : allPartMastersCache;
            const partsToDisplay = filteredParts.length > 0 ? filteredParts : allPartMastersCache;
            partsToDisplay.forEach(p => {
                if (p.partno) {
                    const opt = document.createElement('option');
                    opt.value = p.partno;
                    opt.textContent = p.partno;
                    if (selectedPart && selectedPart.trim().toUpperCase() === p.partno.trim().toUpperCase()) {
                        opt.selected = true;
                    }
                    partSel.appendChild(opt);
                }
            });
        }
    }

    document.getElementById('issueDeptSelect')?.addEventListener('change', (e) => {
        filterIssueDropdownsByDept(e.target.value);
    });

    async function updateBatchDropdownForSpec(spec, selectedBatch = '') {
        const batchSel = document.getElementById('issueBatchNoSelect');
        const availInput = document.getElementById('issueAvailableQtyInput');
        batchSel.innerHTML = '<option value="">-- Select Batch --</option>';
        availInput.value = '0';

        if (!spec) return;

        try {
            const res = await fetch('/api/insert_receipts');
            allReceiptsCache = await res.json();

            const matchingReceipts = allReceiptsCache.filter(r => (r.insert_spec || '').trim().toLowerCase() === spec.trim().toLowerCase() && r.qty >= 0);
            
            if (matchingReceipts.length === 0) {
                batchSel.innerHTML = '<option value="">-- No Batches Available --</option>';
                return;
            }

            matchingReceipts.forEach(r => {
                const bNo = r.batch_no || `ID-${r.id}`;
                const opt = document.createElement('option');
                opt.value = bNo;
                opt.setAttribute('data-qty', r.qty);
                opt.setAttribute('data-receipt-id', r.id);
                opt.textContent = `${bNo} (Avail Qty: ${r.qty})`;
                if (selectedBatch && selectedBatch.trim().toLowerCase() === bNo.trim().toLowerCase()) {
                    opt.selected = true;
                    availInput.value = r.qty;
                }
                batchSel.appendChild(opt);
            });

            if (!selectedBatch && matchingReceipts.length > 0) {
                batchSel.selectedIndex = 1;
                availInput.value = matchingReceipts[0].qty;
            }
        } catch (e) { console.error(e); }
    }

    async function updateOpnDropdownForPart(partno, selectedOpn = '') {
        const opnSel = document.getElementById('issueOpnNoSelect');
        opnSel.innerHTML = '<option value="">-- Select Operation --</option>';
        if (!partno) return;

        const partObj = allPartMastersCache.find(p => (p.partno || '').trim().toUpperCase() === partno.trim().toUpperCase());
        if (!partObj) return;

        try {
            const res = await fetch(`/api/partmaster/${partObj.id}/operations`);
            const ops = await res.json();
            ops.sort((a, b) => (parseInt(a.opn_no) || 0) - (parseInt(b.opn_no) || 0));
            ops.forEach(o => {
                const opt = document.createElement('option');
                opt.value = o.opn_no;
                opt.textContent = `${o.opn_no} - ${o.description || ''}`;
                if (selectedOpn && selectedOpn.trim().toLowerCase() === (o.opn_no || '').trim().toLowerCase()) {
                    opt.selected = true;
                }
                opnSel.appendChild(opt);
            });
        } catch (e) { console.error(e); }
    }

    document.getElementById('issueInsertSpecSelect')?.addEventListener('change', (e) => {
        updateBatchDropdownForSpec(e.target.value);
    });

    document.getElementById('issueBatchNoSelect')?.addEventListener('change', (e) => {
        const selOpt = e.target.options[e.target.selectedIndex];
        const qty = selOpt ? selOpt.getAttribute('data-qty') : 0;
        document.getElementById('issueAvailableQtyInput').value = qty || 0;
    });

    document.getElementById('issuePartNoSelect')?.addEventListener('change', (e) => {
        updateOpnDropdownForPart(e.target.value);
    });

    async function openInsertIssueModal(item = null) {
        if (!insertIssueModal) return;
        const container = document.getElementById('usageEntriesContainer');
        if (container) container.innerHTML = '';

        if (item) {
            document.getElementById('insertIssueModalTitle').textContent = 'Edit Insert Issue';
            document.getElementById('insertIssueId').value = item.id;
            document.getElementById('issueDateInput').value = item.date || '';
            document.getElementById('issueQtyInput').value = item.qty_issued || 1;
            await populateIssueModalDropdowns(item.department, item.insert_spec, item.batch_no, item.partno, item.opn_no);

            let usages = [];
            if (item.usages) {
                try {
                    let parsed = item.usages;
                    while (typeof parsed === 'string') {
                        parsed = JSON.parse(parsed);
                    }
                    if (Array.isArray(parsed)) usages = parsed;
                } catch(e) {}
            }
            if (!usages || !Array.isArray(usages) || usages.length === 0) {
                usages = [{
                    machine: item.machine || '',
                    operator: item.operator || '',
                    partno: item.partno || '',
                    opn_no: item.opn_no || ''
                }];
            }
            usages.forEach(u => createUsageCard(u));
        } else {
            document.getElementById('insertIssueModalTitle').textContent = 'Issue Insert';
            insertIssueForm.reset();
            document.getElementById('insertIssueId').value = '';
            document.getElementById('issueDateInput').valueAsDate = new Date();
            await populateIssueModalDropdowns();
            createUsageCard();
        }
        insertIssueModal.classList.add('show');
    }

    if (addInsertIssueBtn) addInsertIssueBtn.addEventListener('click', () => openInsertIssueModal());
    if (cancelInsertIssueBtn) cancelInsertIssueBtn.addEventListener('click', () => insertIssueModal.classList.remove('show'));
    if (closeInsertIssueModalBtn) closeInsertIssueModalBtn.addEventListener('click', () => insertIssueModal.classList.remove('show'));

    document.getElementById('importInsertIssueBtn')?.addEventListener('click', () => {
        document.getElementById('importInsertIssueInput')?.click();
    });

    const importInsertIssueInput = document.getElementById('importInsertIssueInput');
    if (importInsertIssueInput) {
        importInsertIssueInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = async (evt) => {
                try {
                    const data = evt.target.result;
                    const workbook = XLSX.read(data, { type: 'binary' });
                    const firstSheetName = workbook.SheetNames[0];
                    const worksheet = workbook.Sheets[firstSheetName];
                    const json = XLSX.utils.sheet_to_json(worksheet);

                    if (!json || json.length === 0) {
                        alert('No valid data found in Excel sheet.');
                        return;
                    }

                    const issues = [];
                    const todayStr = new Date().toISOString().slice(0, 10);
                    json.forEach(row => {
                        let dateVal = todayStr;
                        let specVal = '';
                        let batchVal = '';
                        let qtyVal = 1;
                        let machineVal = '';
                        let opVal = '';
                        let partVal = '';
                        let opnVal = '';

                        for (const key of Object.keys(row)) {
                            const k = key.trim().toLowerCase();
                            if (['date', 'issue date', 'issue_date'].includes(k)) dateVal = String(row[key] || '').trim();
                            if (['insert spec', 'insert_spec', 'spec'].includes(k)) specVal = String(row[key] || '').trim();
                            if (['batch no', 'batch_no', 'batch'].includes(k)) batchVal = String(row[key] || '').trim();
                            if (['qty issued', 'qty_issued', 'qty', 'issued qty'].includes(k)) qtyVal = parseInt(row[key]) || 1;
                            if (['machine', 'machine name', 'm/c'].includes(k)) machineVal = String(row[key] || '').trim();
                            if (['operator', 'operator name'].includes(k)) opVal = String(row[key] || '').trim();
                            if (['part no', 'partno', 'part_no'].includes(k)) partVal = String(row[key] || '').trim();
                            if (['opn no', 'opn_no', 'opn', 'operation'].includes(k)) opnVal = String(row[key] || '').trim();
                        }

                        if (specVal) {
                            issues.push({
                                date: dateVal || todayStr,
                                insert_spec: specVal,
                                batch_no: batchVal,
                                qty_issued: qtyVal,
                                machine: machineVal,
                                operator: opVal,
                                partno: partVal,
                                opn_no: opnVal
                            });
                        }
                    });

                    if (issues.length === 0) {
                        alert('No valid issue records found in Excel sheet. Make sure headers are "Date", "Insert Spec", "Batch No", "Qty Issued", "Machine", "Operator", "Part No", and "Opn No".');
                        return;
                    }

                    const res = await fetch('/api/insert_issues/bulk', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ issues })
                    });

                    if (res.ok) {
                        alert(`Successfully imported ${issues.length} Insert Issue records and updated batch stocks!`);
                        fetchInsertIssues();
                    } else {
                        alert('Error importing Excel data.');
                    }
                } catch (err) {
                    console.error('Error importing Insert Issue Excel:', err);
                    alert('Error reading Excel file.');
                } finally {
                    importInsertIssueInput.value = '';
                }
            };
            reader.readAsBinaryString(file);
        });
    }

    if (insertIssueForm) {
        insertIssueForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('insertIssueId').value;
            const batchSel = document.getElementById('issueBatchNoSelect');
            const selectedOpt = batchSel.options[batchSel.selectedIndex];
            const receiptId = selectedOpt ? selectedOpt.getAttribute('data-receipt-id') : null;

            const mach = document.getElementById('issueMachineSelect').value;
            const op = document.getElementById('issueOperatorSelect').value;
            const part = document.getElementById('issuePartNoSelect').value;
            const opn = document.getElementById('issueOpnNoSelect').value;

            let usagesList = [{ machine: mach, operator: op, partno: part, opn_no: opn }];

            if (id) {
                try {
                    const res = await fetch(`/api/insert_issues/${id}`);
                    if (res.ok) {
                        const existing = await res.json();
                        if (existing.usages) {
                            try {
                                let parsed = existing.usages;
                                while (typeof parsed === 'string') {
                                    parsed = JSON.parse(parsed);
                                }
                                if (Array.isArray(parsed) && parsed.length > 1) {
                                    parsed[0] = { machine: mach, operator: op, partno: part, opn_no: opn };
                                    usagesList = parsed;
                                }
                            } catch(e) {}
                        }
                    }
                } catch(e) {}
            }

            const payload = {
                date: document.getElementById('issueDateInput').value,
                department: document.getElementById('issueDeptSelect').value,
                insert_spec: document.getElementById('issueInsertSpecSelect').value,
                batch_no: batchSel.value,
                qty_issued: parseInt(document.getElementById('issueQtyInput').value) || 1,
                machine: mach,
                operator: op,
                partno: part,
                opn_no: opn,
                usages: JSON.stringify(usagesList),
                receipt_id: receiptId ? parseInt(receiptId) : null
            };
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/insert_issues/${id}` : '/api/insert_issues';

            try {
                const res = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    insertIssueModal.classList.remove('show');
                    fetchInsertIssues();
                } else {
                    alert('Error saving issue record');
                }
            } catch (err) { console.error(err); alert('Error saving issue record'); }
        });
    }

    // ====== INSERT MONITOR MODAL ======
    const insertMonitorModal = document.getElementById('insertMonitorModal');
    const closeInsertMonitorModalBtn = document.getElementById('closeInsertMonitorModalBtn');
    const cancelInsertMonitorBtn = document.getElementById('cancelInsertMonitorBtn');
    const saveInsertMonitorBtn = document.getElementById('saveInsertMonitorBtn');
    let currentMonitorIssueItem = null;
    let currentMonitorUidx = 0;

    if (closeInsertMonitorModalBtn) closeInsertMonitorModalBtn.addEventListener('click', () => insertMonitorModal.classList.remove('show'));
    if (cancelInsertMonitorBtn) cancelInsertMonitorBtn.addEventListener('click', () => insertMonitorModal.classList.remove('show'));

    async function openInsertMonitorModal(item, targetUidx = 0) {
        if (!insertMonitorModal || !item) return;
        currentMonitorIssueItem = item;
        currentMonitorUidx = targetUidx;

        let usages = [];
        if (item.usages) {
            try {
                let parsed = item.usages;
                while (typeof parsed === 'string') {
                    parsed = JSON.parse(parsed);
                }
                if (Array.isArray(parsed)) usages = parsed;
            } catch(e) {}
        }
        if (!usages || !Array.isArray(usages) || usages.length === 0) {
            usages = [{
                machine: item.machine || '',
                operator: item.operator || '',
                partno: item.partno || '',
                opn_no: item.opn_no || ''
            }];
        }

        const currentUsage = usages[targetUidx] || usages[0];

        const subtitleEl = document.getElementById('monitorSubtitle');
        if (subtitleEl) {
            subtitleEl.textContent = `${item.insert_spec || ''} | Part: ${currentUsage.partno || item.partno || '-'} | Opn: ${currentUsage.opn_no || item.opn_no || '-'} | Batch: ${item.batch_no || '-'}`;
        }

        let numEdges = 4;
        try {
            const specRes = await fetch('/api/insert_masters');
            const specs = await specRes.json();
            const master = specs.find(s => (s.insert_spec || s.name || '').trim().toLowerCase() === (item.insert_spec || '').trim().toLowerCase());
            if (master) {
                numEdges = parseInt(master.no_of_edges) || parseInt(master.edges) || 4;
            }
        } catch (e) { console.error(e); }

        const edgeObjNormalized = normalizeEdgeObj(item.edge_data);

        const tbody = document.getElementById('insertMonitorTableBody');
        tbody.innerHTML = '';

        for (let i = 1; i <= numEdges; i++) {
            const tr = document.createElement('tr');
            const info = edgeObjNormalized[String(i)];

            let inputHtml = '';
            if (info && info.qty > 0) {
                if (info.uIdx === targetUidx) {
                    // Used in THIS usage entry -> Editable!
                    inputHtml = `<input type="number" class="edge-qty-input" data-edge="${i}" value="${info.qty}" placeholder="Enter Qty" min="0" style="width: 100%; padding: 0.4rem; border: 1px solid var(--border-color); border-radius: 4px;">`;
                } else {
                    // Used in ANOTHER usage entry -> Disabled with note & blank input
                    const label = info.partno ? info.partno : `Usage #${info.uIdx + 1}`;
                    inputHtml = `
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <input type="number" class="edge-qty-input" data-edge="${i}" value="" placeholder="Filled in ${label}" disabled style="flex: 1; padding: 0.4rem; border: 1px solid var(--border-color); border-radius: 4px; background: rgba(0,0,0,0.05); color: var(--text-muted); opacity: 0.7; cursor: not-allowed;">
                            <span style="font-size: 0.8rem; color: #16a34a; font-weight: 500; white-space: nowrap;">✓ (Filled in ${label}: Qty ${info.qty})</span>
                        </div>
                    `;
                }
            } else {
                // Not used yet -> Blank editable field for this usage!
                inputHtml = `<input type="number" class="edge-qty-input" data-edge="${i}" value="" placeholder="Enter Qty" min="0" style="width: 100%; padding: 0.4rem; border: 1px solid var(--border-color); border-radius: 4px;">`;
            }

            tr.innerHTML = `
                <td style="border: 1px solid #cbd5e1; padding: 6px; text-align: center; font-weight: 600;">Edge ${i}</td>
                <td style="border: 1px solid #cbd5e1; padding: 6px;">
                    ${inputHtml}
                </td>
            `;
            tbody.appendChild(tr);
        }

        updateMonitorTotalQty();

        tbody.querySelectorAll('.edge-qty-input').forEach(input => {
            if (!input.disabled) {
                input.addEventListener('input', updateMonitorTotalQty);
            }
        });

        insertMonitorModal.classList.add('show');
    }

    function updateMonitorTotalQty() {
        const inputs = document.querySelectorAll('#insertMonitorTableBody .edge-qty-input');
        let total = 0;
        inputs.forEach(inp => {
            if (!inp.disabled) {
                total += parseInt(inp.value) || 0;
            }
        });
        const totalSpan = document.getElementById('monitorTotalQty');
        if (totalSpan) totalSpan.textContent = `Total Edge Qty: ${total}`;
    }

    if (saveInsertMonitorBtn) {
        saveInsertMonitorBtn.addEventListener('click', async () => {
            if (!currentMonitorIssueItem) return;
            const inputs = document.querySelectorAll('#insertMonitorTableBody .edge-qty-input');

            try {
                const getRes = await fetch(`/api/insert_issues/${currentMonitorIssueItem.id}`);
                const freshItem = getRes.ok ? await getRes.json() : currentMonitorIssueItem;

                let usages = [];
                if (freshItem.usages) {
                    try {
                        let parsed = freshItem.usages;
                        while (typeof parsed === 'string') {
                            parsed = JSON.parse(parsed);
                        }
                        if (Array.isArray(parsed)) usages = parsed;
                    } catch(e) {}
                }
                if (!usages || !Array.isArray(usages) || usages.length === 0) {
                    usages = [{
                        machine: freshItem.machine || '',
                        operator: freshItem.operator || '',
                        partno: freshItem.partno || '',
                        opn_no: freshItem.opn_no || ''
                    }];
                }

                const currentUsage = usages[currentMonitorUidx] || usages[0];
                const activePartno = currentUsage.partno || freshItem.partno || '';

                const normalized = normalizeEdgeObj(freshItem.edge_data);

                inputs.forEach(inp => {
                    if (inp.disabled) return;
                    const edgeNo = inp.getAttribute('data-edge');
                    const val = parseInt(inp.value) || 0;
                    if (val > 0) {
                        normalized[edgeNo] = {
                            qty: val,
                            uIdx: currentMonitorUidx,
                            partno: activePartno
                        };
                    } else {
                        if (normalized[edgeNo] && normalized[edgeNo].uIdx === currentMonitorUidx) {
                            delete normalized[edgeNo];
                        }
                    }
                });

                const payload = {
                    date: freshItem.date || '',
                    department: freshItem.department || '',
                    insert_spec: freshItem.insert_spec || '',
                    batch_no: freshItem.batch_no || '',
                    qty_issued: freshItem.qty_issued || 1,
                    machine: freshItem.machine || '',
                    operator: freshItem.operator || '',
                    partno: freshItem.partno || '',
                    opn_no: freshItem.opn_no || '',
                    usages: freshItem.usages || '',
                    receipt_id: freshItem.receipt_id || null,
                    edge_data: JSON.stringify(normalized)
                };

                const res = await fetch(`/api/insert_issues/${currentMonitorIssueItem.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    insertMonitorModal.classList.remove('show');
                    fetchInsertIssues();
                } else {
                    alert('Error saving Edge Qty');
                }
            } catch (err) { console.error(err); alert('Error saving Edge Qty'); }
        });
    }

    // ====== BREAKDOWN SLIP (B/D SLIP) LOGIC ======
    const bdSlipModal = document.getElementById('bdSlipModal');
    const bdSlipForm = document.getElementById('bdSlipForm');
    const addBdSlipBtn = document.getElementById('addBdSlipBtn');
    const cancelBdSlipBtn = document.getElementById('cancelBdSlipBtn');
    const closeBdSlipModalBtn = document.getElementById('closeBdSlipModalBtn');

    async function fetchBdSlips() {
        try {
            const res = await fetch('/api/breakdown_slips');
            const data = await res.json();
            renderBdSlips(data);
        } catch (err) { console.error('Error fetching breakdown slips:', err); }
    }

    function renderBdSlips(slips) {
        const tbody = document.getElementById('bdSlipBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!slips || slips.length === 0) {
            tbody.innerHTML = '<tr><td colspan="11" style="text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 0.75rem;">No breakdown slips found. Click "+ Add Breakdown Slip" to create a record.</td></tr>';
            return;
        }

        slips.forEach(item => {
            const tr = document.createElement('tr');
            const isSignedOff = item.status === 'Signed Off' || (item.signoff_date_time && item.signoff_date_time.trim() !== '');
            const statusBadge = isSignedOff 
                ? '<span style="color: #16a34a; font-weight: 600; background: #dcfce7; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">Signed Off</span>' 
                : '<span style="color: #d97706; font-weight: 600; background: #fef3c7; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">Open</span>';

            const formattedDateTime = item.date_time ? item.date_time.replace('T', ' ') : '';
            const formattedSignoff = item.signoff_date_time ? item.signoff_date_time.replace('T', ' ') : '-';

            tr.innerHTML = `
                <td>${item.id}</td>
                <td><span style="font-weight: 500;">${formattedDateTime}</span></td>
                <td>${item.department || ''}</td>
                <td>${item.shift || ''}</td>
                <td><strong>${item.maint_type || 'Breakdown'}</strong></td>
                <td>${item.request_by || ''}</td>
                <td><strong>${item.machine || ''}</strong></td>
                <td style="max-width: 200px; white-space: pre-wrap; font-size: 0.85rem;">${item.problem || ''}</td>
                <td>${formattedSignoff}</td>
                <td>${statusBadge}</td>
                <td class="actions-cell">
                    ${!isSignedOff ? `<button class="btn btn-outline signoff-bd-btn" data-id="${item.id}" style="padding: 0.3rem 0.6rem; font-size: 0.8rem; color: #16a34a; border-color: #16a34a; margin-right: 4px;">Sign-off</button>` : ''}
                    <button class="btn btn-outline edit-bd-btn" data-id="${item.id}" style="padding: 0.3rem 0.6rem; font-size: 0.8rem; margin-right: 4px;">Edit</button>
                    <button class="btn btn-outline delete-bd-btn" data-id="${item.id}" style="padding: 0.3rem 0.6rem; font-size: 0.8rem; color: #ef4444; border-color: #ef4444;">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        tbody.querySelectorAll('.signoff-bd-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.target.getAttribute('data-id');
                const now = new Date();
                const nowStr = new Date(now.getTime() - (now.getTimezoneOffset() * 60000)).toISOString().slice(0, 16);
                const res = await fetch('/api/breakdown_slips');
                const data = await res.json();
                const item = data.find(x => x.id == id);
                if (item) {
                    item.signoff_date_time = nowStr;
                    item.status = 'Signed Off';
                    try {
                        const updateRes = await fetch(`/api/breakdown_slips/${id}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(item)
                        });
                        if (updateRes.ok) fetchBdSlips();
                    } catch(err) { console.error(err); }
                }
            });
        });

        tbody.querySelectorAll('.edit-bd-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.target.getAttribute('data-id');
                const res = await fetch('/api/breakdown_slips');
                const data = await res.json();
                const item = data.find(x => x.id == id);
                if (item) openBdSlipModal(item);
            });
        });

        tbody.querySelectorAll('.delete-bd-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                if (confirm('Delete this Breakdown Slip record?')) {
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/breakdown_slips/${id}`, { method: 'DELETE' });
                        if (res.ok) fetchBdSlips();
                        else alert('Error deleting breakdown slip');
                    } catch (err) { console.error(err); }
                }
            });
        });
    }

    async function openBdSlipModal(item = null) {
        if (!bdSlipModal) return;

        const [deptRes, shiftRes, machRes] = await Promise.all([
            fetch('/api/departments'),
            fetch('/api/shifts'),
            fetch('/api/machines')
        ]);
        const depts = await deptRes.json();
        const shifts = await shiftRes.json();
        const machines = await machRes.json();

        const deptSel = document.getElementById('bdDeptSelect');
        deptSel.innerHTML = '<option value="">-- Select Dept --</option>';
        depts.forEach(d => {
            deptSel.innerHTML += `<option value="${d.name}">${d.name}</option>`;
        });

        const shiftSel = document.getElementById('bdShiftSelect');
        shiftSel.innerHTML = '<option value="">-- Select Shift --</option>';
        shifts.forEach(s => {
            shiftSel.innerHTML += `<option value="${s.name}">${s.name}</option>`;
        });

        const updateMachineDropdown = (selectedDept, currentMach = '') => {
            const machSel = document.getElementById('bdMachineSelect');
            machSel.innerHTML = '<option value="">-- Select Machine --</option>';
            const cleanDept = (selectedDept || '').trim().toUpperCase();
            let filtered = machines;
            if (cleanDept) {
                const matches = machines.filter(m => (m.department || '').trim().toUpperCase() === cleanDept);
                if (matches.length > 0) filtered = matches;
            }
            filtered.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.name;
                opt.textContent = m.name;
                if (m.name === currentMach) opt.selected = true;
                machSel.appendChild(opt);
            });
        };

        deptSel.onchange = (e) => {
            updateMachineDropdown(e.target.value);
        };

        if (item) {
            document.getElementById('bdSlipModalTitle').textContent = 'Edit Breakdown Slip';
            document.getElementById('bdSlipId').value = item.id;
            document.getElementById('bdDateTimeInput').value = item.date_time || '';
            document.getElementById('bdDeptSelect').value = item.department || '';
            document.getElementById('bdShiftSelect').value = item.shift || '';
            document.getElementById('bdMaintTypeSelect').value = item.maint_type || 'Breakdown';
            document.getElementById('bdRequestByInput').value = item.request_by || '';
            updateMachineDropdown(item.department || '', item.machine || '');
            document.getElementById('bdProblemInput').value = item.problem || '';
            document.getElementById('bdSignoffDateTimeInput').value = item.signoff_date_time || '';
        } else {
            document.getElementById('bdSlipModalTitle').textContent = 'Create Breakdown Slip';
            bdSlipForm.reset();
            document.getElementById('bdSlipId').value = '';
            const now = new Date();
            const nowStr = new Date(now.getTime() - (now.getTimezoneOffset() * 60000)).toISOString().slice(0, 16);
            document.getElementById('bdDateTimeInput').value = nowStr;
            updateMachineDropdown('');
        }

        bdSlipModal.classList.add('show');
    }

    if (addBdSlipBtn) addBdSlipBtn.addEventListener('click', () => openBdSlipModal());
    if (cancelBdSlipBtn) cancelBdSlipBtn.addEventListener('click', () => bdSlipModal.classList.remove('show'));
    if (closeBdSlipModalBtn) closeBdSlipModalBtn.addEventListener('click', () => bdSlipModal.classList.remove('show'));

    if (bdSlipForm) {
        bdSlipForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('bdSlipId').value;
            const signoffVal = document.getElementById('bdSignoffDateTimeInput').value;

            const payload = {
                date_time: document.getElementById('bdDateTimeInput').value,
                department: document.getElementById('bdDeptSelect').value,
                shift: document.getElementById('bdShiftSelect').value,
                maint_type: document.getElementById('bdMaintTypeSelect').value,
                request_by: document.getElementById('bdRequestByInput').value.trim(),
                machine: document.getElementById('bdMachineSelect').value,
                problem: document.getElementById('bdProblemInput').value.trim(),
                signoff_date_time: signoffVal,
                status: signoffVal ? 'Signed Off' : 'Open'
            };

            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/breakdown_slips/${id}` : '/api/breakdown_slips';

            try {
                const res = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    bdSlipModal.classList.remove('show');
                    fetchBdSlips();
                } else {
                    alert('Error saving Breakdown Slip');
                }
            } catch (err) {
                console.error(err);
                alert('Error saving Breakdown Slip');
            }
        });
    }

    // ====== SERVICE DETAILS LOGIC ======
    let openBreakdownSlipsMap = {};
    let currentServiceDetailId = null;

    async function initServiceDetails() {
        showServiceFormView();
        await loadOpenBreakdownMachinesDropdown();
        fetchServiceHistory();
    }

    function showServiceFormView() {
        const formCont = document.getElementById('sdFormContainer');
        const histCont = document.getElementById('sdHistoryContainer');
        const toggleBtn = document.getElementById('sdToggleViewBtn');
        if (formCont) formCont.style.display = 'block';
        if (histCont) histCont.style.display = 'none';
        if (toggleBtn) toggleBtn.textContent = 'View Service History';
    }

    function showServiceHistoryView() {
        const formCont = document.getElementById('sdFormContainer');
        const histCont = document.getElementById('sdHistoryContainer');
        const toggleBtn = document.getElementById('sdToggleViewBtn');
        if (formCont) formCont.style.display = 'none';
        if (histCont) histCont.style.display = 'block';
        if (toggleBtn) toggleBtn.textContent = 'Back to Entry Form';
    }

    const sdToggleViewBtn = document.getElementById('sdToggleViewBtn');
    if (sdToggleViewBtn) {
        sdToggleViewBtn.addEventListener('click', () => {
            const formCont = document.getElementById('sdFormContainer');
            if (formCont && formCont.style.display === 'none') {
                showServiceFormView();
            } else {
                showServiceHistoryView();
            }
        });
    }

    const newServiceEntryBtn = document.getElementById('newServiceEntryBtn');
    if (newServiceEntryBtn) {
        newServiceEntryBtn.addEventListener('click', () => {
            resetServiceDetailsForm();
            showServiceFormView();
        });
    }

    async function loadOpenBreakdownMachinesDropdown() {
        const select = document.getElementById('sdBreakdownSelect');
        if (!select) return;
        select.innerHTML = '<option value="">-- Loading Open Breakdown Slips... --</option>';

        try {
            const res = await fetch('/api/breakdown_slips');
            const data = await res.json();
            openBreakdownSlipsMap = {};

            const openSlips = data.filter(s => s.status !== 'Signed Off' && (!s.signoff_date_time || s.signoff_date_time.trim() === ''));

            select.innerHTML = '<option value="">-- Select Open Breakdown Machine --</option>';
            if (openSlips.length === 0) {
                select.innerHTML += '<option value="" disabled>(No open breakdown slips currently available)</option>';
            }

            openSlips.forEach(item => {
                openBreakdownSlipsMap[item.id] = item;
                const probText = item.problem ? item.problem.substring(0, 45) : 'No problem text';
                const opt = document.createElement('option');
                opt.value = item.id;
                opt.textContent = `${item.machine} | ${probText} (Dept: ${item.department || '-'}, ID: ${item.id})`;
                select.appendChild(opt);
            });
        } catch (err) {
            console.error('Error loading breakdown slips:', err);
            select.innerHTML = '<option value="">-- Error loading open breakdowns --</option>';
        }
    }

    const sdBreakdownSelect = document.getElementById('sdBreakdownSelect');
    if (sdBreakdownSelect) {
        sdBreakdownSelect.addEventListener('change', async (e) => {
            const bdId = e.target.value;
            const infoCard = document.getElementById('sdBreakdownInfoCard');
            if (bdId && openBreakdownSlipsMap[bdId]) {
                const item = openBreakdownSlipsMap[bdId];
                document.getElementById('sdInfoId').textContent = item.id;
                document.getElementById('sdInfoDate').textContent = item.date_time ? item.date_time.replace('T', ' ') : '-';
                document.getElementById('sdInfoDept').textContent = item.department || '-';
                document.getElementById('sdInfoMachine').textContent = item.machine || '-';
                document.getElementById('sdInfoRequestBy').textContent = item.request_by || '-';
                document.getElementById('sdInfoProblem').textContent = item.problem || '-';
                if (infoCard) infoCard.style.display = 'block';

                await loadExistingServiceDetailForBreakdown(item.id);
            } else {
                if (infoCard) infoCard.style.display = 'none';
                resetServiceDetailsForm(false);
            }
        });
    }

    async function loadExistingServiceDetailForBreakdown(breakdownSlipId) {
        try {
            const res = await fetch('/api/service_details');
            const list = await res.json();
            const existing = list.find(s => s.breakdown_slip_id == breakdownSlipId);
            if (existing) {
                currentServiceDetailId = existing.id;
                
                // Load Spares Data
                let sparesList = [];
                try { sparesList = JSON.parse(existing.spares_data || '[]'); } catch(e) {}
                sdSparesBody.innerHTML = '';
                if (sparesList.length > 0) {
                    sparesList.forEach(sp => addSpareRow(sp));
                } else {
                    addSpareRow();
                }

                // Load Service Data
                let serviceList = [];
                try { serviceList = JSON.parse(existing.service_data || '[]'); } catch(e) {}
                sdServiceBody.innerHTML = '';
                if (serviceList.length > 0) {
                    serviceList.forEach(srv => addServiceRow(srv));
                } else {
                    addServiceRow();
                }

                // Load Remarks
                document.getElementById('sdRemarksInput').value = existing.remarks || '';
                calcServiceTotals();
            } else {
                currentServiceDetailId = null;
                if (sdSparesBody) sdSparesBody.innerHTML = '';
                if (sdServiceBody) sdServiceBody.innerHTML = '';
                addSpareRow();
                addServiceRow();
                document.getElementById('sdRemarksInput').value = '';
                calcServiceTotals();
            }
        } catch (err) {
            console.error('Error loading existing service detail:', err);
        }
    }

    // Dynamic Spares Rows Logic
    const sdSparesBody = document.getElementById('sdSparesBody');
    const sdAddSpareRowBtn = document.getElementById('sdAddSpareRowBtn');

    function addSpareRow(data = {}) {
        if (!sdSparesBody) return;
        const defaultToday = new Date().toISOString().split('T')[0];
        const tr = document.createElement('tr');
        tr.className = 'spare-row';
        tr.innerHTML = `
            <td style="padding: 6px;"><input type="date" class="spare-date" style="width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px;" value="${data.date || defaultToday}"></td>
            <td style="padding: 6px;"><input type="text" class="spare-name" placeholder="Spare name/spec" style="width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px;" value="${data.part_name || ''}"></td>
            <td style="padding: 6px;"><input type="number" class="spare-qty" min="1" step="1" style="width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px;" value="${data.qty !== undefined ? data.qty : 1}"></td>
            <td style="padding: 6px;"><input type="number" class="spare-unit-cost" min="0" step="0.01" style="width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px;" value="${data.unit_cost || 0}"></td>
            <td style="padding: 6px;"><input type="number" class="spare-total-cost" readonly style="width: 100%; padding: 4px 6px; background: #f1f5f9; font-weight: bold; border: 1px solid #cbd5e1; border-radius: 4px;" value="${data.total_cost || 0}"></td>
            <td style="padding: 6px;">
                <select class="spare-received" style="width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px;">
                    <option value="Yes" ${data.received === 'Yes' || !data.received ? 'selected' : ''}>Yes</option>
                    <option value="No" ${data.received === 'No' ? 'selected' : ''}>No</option>
                </select>
            </td>
            <td style="padding: 6px;"><input type="date" class="spare-date-received" style="width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px;" value="${data.date_received || defaultToday}"></td>
            <td style="padding: 6px;"><input type="text" class="spare-remarks" placeholder="Supplier / remarks" style="width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px;" value="${data.remarks || ''}"></td>
            <td style="padding: 6px; text-align: center;"><button type="button" class="btn btn-outline remove-row-btn" style="padding: 2px 8px; color: #ef4444; border-color: #ef4444; font-weight: bold;">&times;</button></td>
        `;
        sdSparesBody.appendChild(tr);

        const qtyIn = tr.querySelector('.spare-qty');
        const unitIn = tr.querySelector('.spare-unit-cost');
        const totalIn = tr.querySelector('.spare-total-cost');
        const removeBtn = tr.querySelector('.remove-row-btn');

        const updateRowTotal = () => {
            const q = parseFloat(qtyIn.value) || 0;
            const u = parseFloat(unitIn.value) || 0;
            totalIn.value = (q * u).toFixed(2);
            calcServiceTotals();
        };

        qtyIn.addEventListener('input', updateRowTotal);
        unitIn.addEventListener('input', updateRowTotal);

        removeBtn.addEventListener('click', () => {
            tr.remove();
            calcServiceTotals();
        });

        updateRowTotal();
    }

    if (sdAddSpareRowBtn) {
        sdAddSpareRowBtn.addEventListener('click', () => addSpareRow());
    }

    // Dynamic Service Rows Logic
    const sdServiceBody = document.getElementById('sdServiceBody');
    const sdAddServiceRowBtn = document.getElementById('sdAddServiceRowBtn');

    function addServiceRow(data = {}) {
        if (!sdServiceBody) return;
        const tr = document.createElement('tr');
        tr.className = 'service-row';
        tr.innerHTML = `
            <td style="padding: 6px;"><input type="text" class="service-work" placeholder="Work done / action taken" style="width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px;" value="${data.work_done || ''}"></td>
            <td style="padding: 6px;"><input type="text" class="service-tech" placeholder="Technician / vendor name" style="width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px;" value="${data.technician || ''}"></td>
            <td style="padding: 6px;"><input type="datetime-local" class="service-start" style="width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px;" value="${data.start_time || ''}"></td>
            <td style="padding: 6px;"><input type="datetime-local" class="service-end" style="width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px;" value="${data.end_time || ''}"></td>
            <td style="padding: 6px;"><input type="number" class="service-cost" min="0" step="0.01" style="width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px;" value="${data.cost || 0}"></td>
            <td style="padding: 6px; text-align: center;"><button type="button" class="btn btn-outline remove-row-btn" style="padding: 2px 8px; color: #ef4444; border-color: #ef4444; font-weight: bold;">&times;</button></td>
        `;
        sdServiceBody.appendChild(tr);

        const costIn = tr.querySelector('.service-cost');
        const removeBtn = tr.querySelector('.remove-row-btn');

        costIn.addEventListener('input', () => calcServiceTotals());
        removeBtn.addEventListener('click', () => {
            tr.remove();
            calcServiceTotals();
        });

        calcServiceTotals();
    }

    if (sdAddServiceRowBtn) {
        sdAddServiceRowBtn.addEventListener('click', () => addServiceRow());
    }

    function calcServiceTotals() {
        let sparesTotal = 0;
        document.querySelectorAll('.spare-total-cost').forEach(input => {
            sparesTotal += parseFloat(input.value) || 0;
        });

        let serviceTotal = 0;
        document.querySelectorAll('.service-cost').forEach(input => {
            serviceTotal += parseFloat(input.value) || 0;
        });

        const grandTotal = sparesTotal + serviceTotal;

        const sparesIn = document.getElementById('sdSparesTotal');
        const serviceIn = document.getElementById('sdServiceTotal');
        const grandIn = document.getElementById('sdGrandTotal');

        if (sparesIn) sparesIn.value = sparesTotal.toFixed(2);
        if (serviceIn) serviceIn.value = serviceTotal.toFixed(2);
        if (grandIn) grandIn.value = grandTotal.toFixed(2);
    }

    function resetServiceDetailsForm(clearSelect = true) {
        currentServiceDetailId = null;
        if (clearSelect) {
            const select = document.getElementById('sdBreakdownSelect');
            if (select) select.value = '';
            const infoCard = document.getElementById('sdBreakdownInfoCard');
            if (infoCard) infoCard.style.display = 'none';
        }

        if (sdSparesBody) sdSparesBody.innerHTML = '';
        if (sdServiceBody) sdServiceBody.innerHTML = '';

        addSpareRow();
        addServiceRow();

        const remarksIn = document.getElementById('sdRemarksInput');
        if (remarksIn) remarksIn.value = '';

        calcServiceTotals();
    }

    const saveServiceDetailBtn = document.getElementById('saveServiceDetailBtn');
    if (saveServiceDetailBtn) {
        saveServiceDetailBtn.addEventListener('click', async () => {
            const bdIdVal = document.getElementById('sdBreakdownSelect').value;
            if (!bdIdVal && !currentServiceDetailId) {
                alert('Please select an Open Breakdown Machine');
                return;
            }

            const bdItem = openBreakdownSlipsMap[bdIdVal] || {};

            const sparesList = [];
            document.querySelectorAll('.spare-row').forEach(tr => {
                const date = tr.querySelector('.spare-date').value;
                const name = tr.querySelector('.spare-name').value.trim();
                const qty = parseFloat(tr.querySelector('.spare-qty').value) || 0;
                const unit_cost = parseFloat(tr.querySelector('.spare-unit-cost').value) || 0;
                const total_cost = parseFloat(tr.querySelector('.spare-total-cost').value) || 0;
                const received = tr.querySelector('.spare-received').value;
                const date_received = tr.querySelector('.spare-date-received').value;
                const remarks = tr.querySelector('.spare-remarks').value.trim();
                if (name || total_cost > 0 || remarks) {
                    sparesList.push({ date, part_name: name, qty, unit_cost, total_cost, received, date_received, remarks });
                }
            });

            const serviceList = [];
            document.querySelectorAll('.service-row').forEach(tr => {
                const work_done = tr.querySelector('.service-work').value.trim();
                const technician = tr.querySelector('.service-tech').value.trim();
                const start_time = tr.querySelector('.service-start').value;
                const end_time = tr.querySelector('.service-end').value;
                const cost = parseFloat(tr.querySelector('.service-cost').value) || 0;
                if (work_done || technician || cost > 0) {
                    serviceList.push({ work_done, technician, start_time, end_time, cost });
                }
            });

            const spares_cost = parseFloat(document.getElementById('sdSparesTotal').value) || 0;
            const service_cost = parseFloat(document.getElementById('sdServiceTotal').value) || 0;
            const total_cost = parseFloat(document.getElementById('sdGrandTotal').value) || 0;
            const remarks = document.getElementById('sdRemarksInput').value.trim();

            const payload = {
                breakdown_slip_id: parseInt(bdIdVal) || (bdItem.id ? parseInt(bdItem.id) : null),
                machine: bdItem.machine || '',
                spares_data: JSON.stringify(sparesList),
                service_data: JSON.stringify(serviceList),
                spares_cost,
                service_cost,
                total_cost,
                remarks
            };

            const method = currentServiceDetailId ? 'PUT' : 'POST';
            const url = currentServiceDetailId ? `/api/service_details/${currentServiceDetailId}` : '/api/service_details';

            try {
                const res = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    const savedItem = await res.json();
                    currentServiceDetailId = savedItem.id;
                    alert('Service Details saved successfully!');
                    fetchServiceHistory();
                } else {
                    alert('Error saving Service Details');
                }
            } catch (err) {
                console.error(err);
                alert('Error saving Service Details');
            }
        });
    }

    async function fetchServiceHistory() {
        const tbody = document.getElementById('sdHistoryBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        try {
            const res = await fetch('/api/service_details');
            const data = await res.json();
            if (!data || data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 0.75rem;">No service detail history recorded yet.</td></tr>';
                return;
            }

            data.forEach(item => {
                let spareNames = '-';
                try {
                    const spares = JSON.parse(item.spares_data || '[]');
                    const names = spares.map(s => s.part_name ? s.part_name.trim() : '').filter(Boolean);
                    if (names.length > 0) spareNames = names.join(', ');
                } catch(e) {}

                let actionsTaken = '-';
                try {
                    const services = JSON.parse(item.service_data || '[]');
                    const actions = services.map(s => s.work_done ? s.work_done.trim() : '').filter(Boolean);
                    if (actions.length > 0) actionsTaken = actions.join(', ');
                } catch(e) {}

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${item.id}</td>
                    <td>${item.breakdown_slip_id || '-'}</td>
                    <td><strong>${item.machine || '-'}</strong></td>
                    <td style="max-width: 200px; white-space: pre-wrap; font-size: 0.85rem; font-weight: 500; color: #0284c7;">${spareNames}</td>
                    <td style="max-width: 220px; white-space: pre-wrap; font-size: 0.85rem; font-weight: 500; color: #15803d;">${actionsTaken}</td>
                    <td>₹${(item.spares_cost || 0).toFixed(2)}</td>
                    <td>₹${(item.service_cost || 0).toFixed(2)}</td>
                    <td><strong style="color: #0369a1;">₹${(item.total_cost || 0).toFixed(2)}</strong></td>
                    <td style="max-width: 180px; white-space: pre-wrap; font-size: 0.85rem;">${item.remarks || '-'}</td>
                    <td class="actions-cell">
                        <button class="btn btn-outline delete-sd-btn" data-id="${item.id}" style="padding: 0.3rem 0.6rem; font-size: 0.8rem; color: #ef4444; border-color: #ef4444;">Delete</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            tbody.querySelectorAll('.delete-sd-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    if (confirm('Delete this Service Detail record?')) {
                        const id = e.target.getAttribute('data-id');
                        try {
                            const delRes = await fetch(`/api/service_details/${id}`, { method: 'DELETE' });
                            if (delRes.ok) fetchServiceHistory();
                        } catch (err) { console.error(err); }
                    }
                });
            });
        } catch (err) { console.error(err); }
    }
});
