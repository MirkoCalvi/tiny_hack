// Dashboard JavaScript - Case filtering and navigation

document.addEventListener('DOMContentLoaded', function () {
    console.log('Dashboard initialized');

    // Category filter functionality
    const categoryFilter = document.getElementById('categoryFilter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', function () {
            const selectedCategory = this.value;
            const caseItems = document.querySelectorAll('.case-item');

            caseItems.forEach(item => {
                if (selectedCategory === 'all') {
                    item.style.display = 'flex';
                } else {
                    const itemCategory = item.getAttribute('data-category');
                    item.style.display = itemCategory === selectedCategory ? 'flex' : 'none';
                }
            });
        });
    }

    // Case item click navigation
    const caseItems = document.querySelectorAll('.case-item');
    caseItems.forEach(item => {
        item.addEventListener('click', function () {
            const captureId = this.getAttribute('data-capture-id');
            window.location.href = `?capture_id=${captureId}`;
        });
    });

    // Auto-refresh functionality (optional - refresh every 30 seconds)
    const enableAutoRefresh = false; // Set to true to enable
    if (enableAutoRefresh) {
        setInterval(function () {
            // Reload page to get new captures
            location.reload();
        }, 30000);
    }

    // Keyboard navigation
    document.addEventListener('keydown', function (e) {
        const activeCase = document.querySelector('.case-item.active');
        if (!activeCase) return;

        let nextCase = null;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            nextCase = activeCase.nextElementSibling;
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            nextCase = activeCase.previousElementSibling;
        }

        if (nextCase && nextCase.classList.contains('case-item')) {
            const captureId = nextCase.getAttribute('data-capture-id');
            window.location.href = `?capture_id=${captureId}`;
        }
    });

    // Add smooth scroll behavior
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // Initialize tooltips for technical details
    const detailRows = document.querySelectorAll('.detail-row');
    detailRows.forEach(row => {
        row.title = 'Click to copy';
        row.style.cursor = 'pointer';

        row.addEventListener('click', function () {
            const value = this.querySelector('.detail-value').textContent;
            navigator.clipboard.writeText(value).then(() => {
                // Visual feedback
                const originalBg = this.style.backgroundColor;
                this.style.backgroundColor = 'rgba(16, 185, 129, 0.2)';
                setTimeout(() => {
                    this.style.backgroundColor = originalBg;
                }, 300);
            });
        });
    });

    console.log('Dashboard features loaded:', {
        totalCases: caseItems.length,
        filterEnabled: !!riskFilter,
        keyboardNavEnabled: true
    });
});
