document.addEventListener('DOMContentLoaded', () => {
    // Shared
    const addBtn = document.getElementById('addBtn');
    const importBtn = document.getElementById('importBtn');
    const importFile = document.getElementById('importFile');
    let currentTab = 'products';
    let availableMachines = [];

    // Tabs
    const tabProducts = document.getElementById('tabProducts');
    const tabPartMaster = document.getElementById('tabPartMaster');
    const tabMachines = document.getElementById('tabMachines');
    const tabOperators = document.getElementById('tabOperators');
    const tabSchedule = document.getElementById('tabSchedule');
    const menuScheduleCreate = document.getElementById('menuScheduleCreate');
    const menuScheduleRun = document.getElementById('menuScheduleRun');
    const menuScheduleStatus = document.getElementById('menuScheduleStatus');
    const tabProdLog = document.getElementById('tabProdLog');
    
    const productsSection = document.getElementById('productsSection');
    const partMasterSection = document.getElementById('partMasterSection');
    const machinesSection = document.getElementById('machinesSection');
    const operatorsSection = document.getElementById('operatorsSection');
    const scheduleCreateSection = document.getElementById('scheduleCreateSection');
    const scheduleRunSection = document.getElementById('scheduleRunSection');
    const scheduleStatusSection = document.getElementById('scheduleStatusSection');
    const prodLogSection = document.getElementById('prodLogSection');

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
        productsSection.style.display = 'none';
        partMasterSection.style.display = 'none';
        machinesSection.style.display = 'none';
        operatorsSection.style.display = 'none';
        scheduleCreateSection.style.display = 'none';
        scheduleRunSection.style.display = 'none';
        scheduleStatusSection.style.display = 'none';
        prodLogSection.style.display = 'none';
        
        tabProducts.classList.remove('active');
        tabPartMaster.classList.remove('active');
        tabMachines.classList.remove('active');
        tabOperators.classList.remove('active');
        tabSchedule.classList.remove('active');
        tabProdLog.classList.remove('active');
        importBtn.style.display = 'none';
        addBtn.style.display = 'inline-flex';
    }

    // Tab Logic
    tabProducts.addEventListener('click', () => {
        currentTab = 'products';
        hideAllSections();
        tabProducts.classList.add('active');
        productsSection.style.display = 'block';
        addBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Tool`;
        fetchProducts();
    });

    tabPartMaster.addEventListener('click', () => {
        currentTab = 'partmaster';
        hideAllSections();
        tabPartMaster.classList.add('active');
        partMasterSection.style.display = 'block';
        importBtn.style.display = 'inline-block';
        addBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Part`;
        fetchPartMasters();
    });

    tabMachines.addEventListener('click', () => {
        currentTab = 'machines';
        hideAllSections();
        tabMachines.classList.add('active');
        machinesSection.style.display = 'block';
        importBtn.style.display = 'inline-block';
        addBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Machine`;
        fetchMachines();
    });

    tabOperators.addEventListener('click', () => {
        currentTab = 'operators';
        hideAllSections();
        tabOperators.classList.add('active');
        operatorsSection.style.display = 'block';
        importBtn.style.display = 'inline-block';
        addBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Operator`;
        fetchOperators();
    });

    menuScheduleCreate.addEventListener('click', (e) => {
        e.preventDefault();
        currentTab = 'schedule-create';
        hideAllSections();
        tabSchedule.classList.add('active');
        scheduleCreateSection.style.display = 'block';
        addBtn.style.display = 'none';
        loadSchedulePartNos();
    });

    menuScheduleRun.addEventListener('click', (e) => {
        e.preventDefault();
        currentTab = 'schedule-run';
        hideAllSections();
        tabSchedule.classList.add('active');
        scheduleRunSection.style.display = 'block';
        addBtn.style.display = 'none';
        fetchRunSchedule();
    });

    menuScheduleStatus.addEventListener('click', (e) => {
        e.preventDefault();
        currentTab = 'schedule-status';
        hideAllSections();
        tabSchedule.classList.add('active');
        scheduleStatusSection.style.display = 'block';
        addBtn.style.display = 'none';
    });

    tabProdLog.addEventListener('click', () => {
        currentTab = 'prod-log';
        hideAllSections();
        tabProdLog.classList.add('active');
        prodLogSection.style.display = 'block';
        addBtn.style.display = 'none';
        initProdLog();
    });

    addBtn.addEventListener('click', () => {
        if (currentTab === 'products') openProductModal(false);
        else if (currentTab === 'partmaster') openPartModal(false);
        else if (currentTab === 'machines') openMachineModal(false);
        else if (currentTab === 'operators') openOperatorModal(false);
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
                        const name = String(row['Operator Name'] || row['operator name'] || row['Operator'] || '').trim();
                        if (!name) return;
                        operators.push({
                            name: name,
                            department: String(row['Dept'] || row['dept'] || row['Department'] || row['department'] || '').trim()
                        });
                    });
                    endpoint = '/api/operators/bulk_import';
                    bodyData = JSON.stringify({ operators: operators });
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
        schedulePartNo.innerHTML = '<option value="">-- Select Part No --</option>';
        allPartMasters.forEach(p => {
            schedulePartNo.innerHTML += `<option value="${p.partno}">${p.partno}</option>`;
        });
    }

    schedulePartNo.addEventListener('change', (e) => {
        const selectedPartNo = e.target.value;
        const part = allPartMasters.find(p => p.partno === selectedPartNo);
        if (part) {
            scheduleDept.value = part.department || '';
        } else {
            scheduleDept.value = '';
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
                    alert('Failed to create schedule.');
                }
            } catch (err) {
                console.error(err);
                alert('Error creating schedule.');
            }
        });
    }

    // Call fetchSchedulesForList when opening the create tab
    menuScheduleCreate.addEventListener('click', (e) => {
        // e.preventDefault() is already handled in the previous listener, but we can just add this logic here or let it be handled when they click the tab.
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
        const partSelect = document.getElementById('prodLogPartNo');
        partSelect.innerHTML = '<option value="">-- Select Scheduled Part --</option>';
        const uniqueSchedParts = [...new Set(prodLogSchedules.map(s => s.partno))];
        uniqueSchedParts.forEach(p => {
            partSelect.innerHTML += `<option value="${p}">${p}</option>`;
        });
        
        fetchProdLogs();
    }

    document.getElementById('prodLogDept').addEventListener('change', (e) => {
        const dept = e.target.value.trim().toUpperCase();
        const machSelect = document.getElementById('prodLogMachine');
        const opSelect = document.getElementById('prodLogOperator');
        const partSelect = document.getElementById('prodLogPartNo');
        
        machSelect.innerHTML = '<option value="">-- Select Machine --</option>';
        opSelect.innerHTML = '<option value="">-- Select Operator --</option>';
        partSelect.innerHTML = '<option value="">-- Select Scheduled Part --</option>';
        
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
            partSelect.innerHTML += `<option value="${p}">${p}</option>`;
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

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${log.date}</td>
                    <td>${log.dept}</td>
                    <td>${log.shift}</td>
                    <td>${log.partno}</td>
                    <td>${log.opn_no}</td>
                    <td>${log.machine}</td>
                    <td><span style="font-weight:bold;color:var(--primary);">${log.prod_qty}</span></td>
                    <td>${log.efficiency}%</td>
                    <td><span style="font-weight:bold;">${totalIdle.toFixed(2)}</span></td>
                    <td>${log.idle_hours || 0}</td>
                    <td>${log.idle_reason === 'None' ? '-' : log.idle_reason}</td>
                    <td>${log.idle_hours_2 || 0}</td>
                    <td>${log.idle_reason_2 === 'None' ? '-' : log.idle_reason_2}</td>
                    <td>${log.idle_hours_3 || 0}</td>
                    <td>${log.idle_reason_3 === 'None' ? '-' : log.idle_reason_3}</td>
                `;
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

});
