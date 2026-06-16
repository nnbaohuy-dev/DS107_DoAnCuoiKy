// Configuration
// If you host the backend somewhere else, replace this URL with your backend URL (e.g. https://my-space.hf.space)
const API_BASE_URL = "https://shreacker-coffee-bean-quality-api.hf.space";

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const previewContainer = document.getElementById('preview-container');
    const imagePreview = document.getElementById('image-preview');
    const analyzeBtn = document.getElementById('analyze-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    
    const uploadSection = document.querySelector('.upload-section');
    const resultSection = document.getElementById('result-section');
    const resultImage = document.getElementById('result-image');
    const resultStats = document.getElementById('result-stats');
    const newAnalysisBtn = document.getElementById('new-analysis-btn');
    
    const overlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');

    let currentFile = null;

    // Ping the backend to wake it up if it's on HF Spaces
    fetch(`${API_BASE_URL}/ping`).catch(e => console.log("Backend might be waking up..."));

    // Event Listeners for Drag & Drop
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
        if (e.dataTransfer.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    browseBtn.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFile(e.target.files[0]);
        }
    });

    cancelBtn.addEventListener('click', () => {
        currentFile = null;
        fileInput.value = "";
        previewContainer.style.display = 'none';
        dropZone.style.display = 'block';
    });

    newAnalysisBtn.addEventListener('click', () => {
        resultSection.style.display = 'none';
        uploadSection.style.display = 'block';
        cancelBtn.click();
    });

    analyzeBtn.addEventListener('click', analyzeImage);

    function handleFile(file) {
        if (!file.type.startsWith('image/')) {
            alert('Please select an image file.');
            return;
        }
        currentFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            dropZone.style.display = 'none';
            previewContainer.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }

    async function analyzeImage() {
        if (!currentFile) return;

        showLoading("Analyzing quality... (This may take a minute if the AI is waking up)");
        
        const formData = new FormData();
        formData.append("file", currentFile);

        try {
            const response = await fetch(`${API_BASE_URL}/predict`, {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || "Failed to analyze image");
            }

            const data = await response.json();
            
            if (data.status === "success") {
                resultImage.src = data.image_base64;
                resultStats.innerText = `Successfully detected and analyzed ${data.beans_detected} coffee beans!`;
                
                uploadSection.style.display = 'none';
                resultSection.style.display = 'block';
            } else {
                throw new Error(data.error || "Unknown error occurred");
            }

        } catch (error) {
            alert("Error: " + error.message);
        } finally {
            hideLoading();
        }
    }

    function showLoading(text) {
        loadingText.innerText = text;
        overlay.classList.add('active');
    }

    function hideLoading() {
        overlay.classList.remove('active');
    }
});
