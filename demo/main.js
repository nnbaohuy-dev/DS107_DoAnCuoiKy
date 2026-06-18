const API_BASE_URL = "https://shreacker-coffee-bean-quality-api.hf.space"; // Ensure this is pointing to your API (local or HF)

// Global State
const appState = {
    currentImageFile: null,
    currentImageDataURL: null,
    analyticsHistory: [] // Will store { timestamp, imageURL, totalBeans, gradeBreakdown }
};

document.addEventListener('DOMContentLoaded', () => {
    // ---- TAB ROUTING LOGIC ----
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active classes
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active to clicked
            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // ---- TAB 1: UPLOAD LOGIC ----
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const uploadContent = document.getElementById('upload-content');
    const previewContainer = document.getElementById('preview-container');
    const imagePreview = document.getElementById('image-preview');
    const cancelBtn = document.getElementById('cancel-btn');
    const analyzeBtn = document.getElementById('analyze-btn');
    
    // Output UI
    const outputPlaceholder = document.getElementById('output-placeholder');
    const resultContent = document.getElementById('result-content');
    const resultImage = document.getElementById('result-image');
    const beanCounter = document.getElementById('bean-counter');
    const loadingOverlay = document.getElementById('loading-overlay');

    browseBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    cancelBtn.addEventListener('click', () => {
        appState.currentImageFile = null;
        appState.currentImageDataURL = null;
        
        // Reset Left Panel
        uploadContent.style.display = 'block';
        previewContainer.style.display = 'none';
        fileInput.value = '';
        
        // Reset Right Panel
        outputPlaceholder.style.display = 'flex';
        resultContent.style.display = 'none';
    });

    function handleFile(file) {
        if (!file.type.startsWith('image/')) {
            alert('Please select an image file');
            return;
        }

        appState.currentImageFile = file;

        const reader = new FileReader();
        reader.onload = (e) => {
            appState.currentImageDataURL = e.target.result;
            imagePreview.src = e.target.result;
            uploadContent.style.display = 'none';
            previewContainer.style.display = 'flex';
            
            // Reset right panel for new image
            outputPlaceholder.style.display = 'flex';
            resultContent.style.display = 'none';
        };
        reader.readAsDataURL(file);
    }

    // ---- TAB 1: INFERENCE & COUNTER LOGIC ----
    analyzeBtn.addEventListener('click', async () => {
        if (!appState.currentImageFile) return;

        loadingOverlay.style.display = 'flex';

        const formData = new FormData();
        formData.append("file", appState.currentImageFile);

        try {
            const response = await fetch(`${API_BASE_URL}/predict`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to analyze image');
            }

            // Update Right Panel UI
            resultImage.src = data.image_base64;
            const breakdown = data.breakdown || {};
            
            beanCounter.innerHTML = '';
            for (const [grade, count] of Object.entries(breakdown)) {
                beanCounter.innerHTML += `
                    <div class="counter-card">
                        <div class="counter-label">Grade ${grade}</div>
                        <div class="counter-value">${count}</div>
                    </div>
                `;
            }

            // Also show total
            beanCounter.innerHTML += `
                <div class="counter-card" style="border-color: var(--accent-color);">
                    <div class="counter-label">Total Detected</div>
                    <div class="counter-value">${data.beans_detected}</div>
                </div>
            `;

            outputPlaceholder.style.display = 'none';
            resultContent.style.display = 'block';

            // Log to Analytics
            logToAnalytics(appState.currentImageDataURL, data.beans_detected, breakdown);

        } catch (error) {
            console.error('Error:', error);
            alert('Error analyzing image: ' + error.message);
        } finally {
            loadingOverlay.style.display = 'none';
        }
    });

    // ---- TAB 3: SAMPLE GALLERY LOGIC ----
    const loadSampleBtns = document.querySelectorAll('.load-sample-btn');
    loadSampleBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const imgSrc = e.target.getAttribute('data-src');
            
            // Switch to Predict Tab
            document.querySelector('[data-tab="tab-predict"]').click();
            
            // Fetch the image to convert it into a File object for the pipeline
            loadingOverlay.style.display = 'flex';
            document.getElementById('loading-text').innerText = "Loading sample...";
            
            try {
                const res = await fetch(imgSrc);
                const blob = await res.blob();
                const file = new File([blob], "sample.png", { type: "image/png" });
                
                // Inject to state
                handleFile(file);
                
                // Auto trigger analysis after a short delay for UI to update
                setTimeout(() => {
                    document.getElementById('loading-text').innerText = "Waking up the AI model (this may take a minute)...";
                    analyzeBtn.click();
                }, 500);
            } catch(err) {
                alert("Failed to load sample: " + err);
                loadingOverlay.style.display = 'none';
            }
        });
    });

    // ---- TAB 4: ANALYTICS LOGIC ----
    function logToAnalytics(thumbnailURL, totalBeans, breakdown) {
        const now = new Date();
        const timestamp = now.toLocaleDateString() + ' ' + now.toLocaleTimeString();
        
        let breakdownStr = Object.entries(breakdown).map(([g, c]) => `${g}: ${c}`).join(', ');
        
        appState.analyticsHistory.push({
            timestamp,
            thumbnailURL,
            totalBeans,
            breakdownStr
        });

        renderAnalyticsTable();
    }

    function renderAnalyticsTable() {
        const tbody = document.getElementById('session-tbody');
        if (appState.analyticsHistory.length === 0) return;
        
        tbody.innerHTML = ''; // Clear empty state
        
        appState.analyticsHistory.forEach(log => {
            tbody.innerHTML += `
                <tr>
                    <td>${log.timestamp}</td>
                    <td><img src="${log.thumbnailURL}" class="thumb-img" alt="thumb"></td>
                    <td>${log.totalBeans}</td>
                    <td>${log.breakdownStr}</td>
                </tr>
            `;
        });
    }

    const exportBtn = document.getElementById('export-csv-btn');
    exportBtn.addEventListener('click', () => {
        if (appState.analyticsHistory.length === 0) {
            alert("No data to export!");
            return;
        }

        let csvContent = "data:text/csv;charset=utf-8,Timestamp,Total Beans,Grade Breakdown\n";
        
        appState.analyticsHistory.forEach(log => {
            const safeBreakdown = `"${log.breakdownStr}"`; // wrap in quotes to escape commas
            csvContent += `${log.timestamp},${log.totalBeans},${safeBreakdown}\n`;
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "coffee_session_analytics.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
});
