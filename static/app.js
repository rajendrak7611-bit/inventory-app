document.addEventListener('DOMContentLoaded', () => {
    // Shared
    const addBtn = document.getElementById('addBtn');
    let currentTab = 'products';

    // Tabs
    const tabProducts = document.getElementById('tabProducts');
    const tabPartMaster = document.getElementById('tabPartMaster');
    const productsSection = document.getElementById('productsSection');
    const partMasterSection = document.getElementById('partMasterSection');

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

    // Tab Logic
    tabProducts.addEventListener('click', () => {
        currentTab = 'products';
        tabProducts.classList.add('active');
        tabPartMaster.classList.remove('active');
        productsSection.style.display = 'block';
        partMasterSection.style.display = 'none';
        addBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Tool`;
        fetchProducts();
    });

    tabPartMaster.addEventListener('click', () => {
        currentTab = 'partmaster';
        tabPartMaster.classList.add('active');
        tabProducts.classList.remove('active');
        partMasterSection.style.display = 'block';
        productsSection.style.display = 'none';
        addBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Add Part`;
        fetchPartMasters();
    });

    addBtn.addEventListener('click', () => {
        if (currentTab === 'products') {
            openProductModal(false);
        } else {
            openPartModal(false);
        }
    });

    // --- PRODUCTS LOGIC ---
    async function fetchProducts() {
        try {
            const response = await fetch('/api/products');
            const products = await response.json();
            renderProductsTable(products);
        } catch (error) {
            console.error('Error fetching products:', error);
        }
    }

    function renderProductsTable(products) {
        productsBody.innerHTML = '';
        if (products.length === 0) {
            productsBody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted)">No tools found. Add one!</td></tr>';
            return;
        }

        products.forEach(product => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${product.id}</td>
                <td>${product.family}</td>
                <td>${product.spec}</td>
                <td>${product.make}</td>
                <td>${product.stock}</td>
                <td>Rs ${product.price.toFixed(2)}</td>
                <td class="actions">
                    <button class="btn btn-edit" onclick="editProduct(${product.id})">Edit</button>
                    <button class="btn btn-danger" onclick="deleteProduct(${product.id})">Delete</button>
                </td>
            `;
            productsBody.appendChild(tr);
        });
    }

    function openProductModal(isEdit = false) {
        productModal.classList.add('show');
        productModalTitle.textContent = isEdit ? 'Edit Tool' : 'Add Tool';
    }

    function closeProductModal() {
        productModal.classList.remove('show');
        productForm.reset();
        document.getElementById('productId').value = '';
    }

    closeProductBtn.addEventListener('click', closeProductModal);
    cancelProductBtn.addEventListener('click', closeProductModal);

    productForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('productId').value;
        const data = {
            family: document.getElementById('family').value,
            spec: document.getElementById('spec').value,
            make: document.getElementById('make').value,
            stock: parseInt(document.getElementById('stock').value),
            price: parseFloat(document.getElementById('price').value)
        };
        const isEdit = id !== '';
        const url = isEdit ? `/api/products/${id}` : '/api/products';
        
        try {
            const response = await fetch(url, {
                method: isEdit ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (response.ok) {
                closeProductModal();
                fetchProducts();
            }
        } catch (error) { console.error(error); }
    });

    window.deleteProduct = async (id) => {
        if (confirm('Are you sure you want to delete this tool?')) {
            try {
                const response = await fetch(`/api/products/${id}`, { method: 'DELETE' });
                if (response.ok) fetchProducts();
            } catch (error) { console.error(error); }
        }
    };

    window.editProduct = async (id) => {
        try {
            const response = await fetch('/api/products');
            const products = await response.json();
            const product = products.find(p => p.id === id);
            if (product) {
                document.getElementById('productId').value = product.id;
                document.getElementById('family').value = product.family;
                document.getElementById('spec').value = product.spec;
                document.getElementById('make').value = product.make;
                document.getElementById('stock').value = product.stock;
                document.getElementById('price').value = product.price;
                openProductModal(true);
            }
        } catch (error) { console.error(error); }
    };

    // --- PART MASTER LOGIC ---
    async function fetchPartMasters() {
        try {
            const response = await fetch('/api/partmaster');
            const parts = await response.json();
            renderPartMasterTable(parts);
        } catch (error) {
            console.error('Error fetching part masters:', error);
        }
    }

    function renderPartMasterTable(parts) {
        partMasterBody.innerHTML = '';
        if (parts.length === 0) {
            partMasterBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">No part masters found. Add one!</td></tr>';
            return;
        }

        parts.forEach(part => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${part.id}</td>
                <td>${part.family}</td>
                <td>${part.forge_pn}</td>
                <td>${part.partno}</td>
                <td class="actions">
                    <button class="btn btn-edit" onclick="editPartMaster(${part.id})">Edit</button>
                    <button class="btn btn-danger" onclick="deletePartMaster(${part.id})">Delete</button>
                </td>
            `;
            partMasterBody.appendChild(tr);
        });
    }

    function openPartModal(isEdit = false) {
        partModal.classList.add('show');
        partModalTitle.textContent = isEdit ? 'Edit Part Master' : 'Add Part Master';
    }

    function closePartModal() {
        partModal.classList.remove('show');
        partForm.reset();
        document.getElementById('partId').value = '';
    }

    closePartBtn.addEventListener('click', closePartModal);
    cancelPartBtn.addEventListener('click', closePartModal);

    partForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('partId').value;
        const data = {
            family: document.getElementById('partFamily').value,
            forge_pn: document.getElementById('forgePn').value,
            partno: document.getElementById('partno').value
        };
        const isEdit = id !== '';
        const url = isEdit ? `/api/partmaster/${id}` : '/api/partmaster';
        
        try {
            const response = await fetch(url, {
                method: isEdit ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (response.ok) {
                closePartModal();
                fetchPartMasters();
            }
        } catch (error) { console.error(error); }
    });

    window.deletePartMaster = async (id) => {
        if (confirm('Are you sure you want to delete this part master?')) {
            try {
                const response = await fetch(`/api/partmaster/${id}`, { method: 'DELETE' });
                if (response.ok) fetchPartMasters();
            } catch (error) { console.error(error); }
        }
    };

    window.editPartMaster = async (id) => {
        try {
            const response = await fetch('/api/partmaster');
            const parts = await response.json();
            const part = parts.find(p => p.id === id);
            if (part) {
                document.getElementById('partId').value = part.id;
                document.getElementById('partFamily').value = part.family;
                document.getElementById('forgePn').value = part.forge_pn;
                document.getElementById('partno').value = part.partno;
                openPartModal(true);
            }
        } catch (error) { console.error(error); }
    };

    // Initial fetch
    fetchProducts();
});
