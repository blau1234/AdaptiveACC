import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

// Three.js scene setup
let scene, camera, renderer, controls;
let currentModel = null;

const canvas = document.getElementById('three-canvas');
const overlay = document.getElementById('viewer-overlay');
const fileInput = document.getElementById('ifc_file');
const placeholder = document.getElementById('preview-placeholder');
const fileInfo = document.getElementById('file-info');
const fileNameDisplay = document.getElementById('file-name-display');
const fileSizeDisplay = document.getElementById('file-size-display');

// Initialize Three.js scene
function initViewer() {
    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a1a);

    // Camera
    const aspect = canvas.clientWidth / canvas.clientHeight;
    camera = new THREE.PerspectiveCamera(75, aspect, 0.1, 2000);
    camera.position.set(5, 5, 5);

    // Renderer
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight1.position.set(10, 10, 10);
    scene.add(directionalLight1);

    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.4);
    directionalLight2.position.set(-10, 10, -10);
    scene.add(directionalLight2);

    // Grid
    const gridHelper = new THREE.GridHelper(20, 20, 0x444444, 0x222222);
    scene.add(gridHelper);

    // Add a demo cube to show the scene works
    const geometry = new THREE.BoxGeometry(1, 1, 1);
    const material = new THREE.MeshStandardMaterial({ color: 0x00ff00 });
    const cube = new THREE.Mesh(geometry, material);
    cube.position.y = 0.5;
    scene.add(cube);

    // Controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(0, 0, 0);

    // Handle window resize
    window.addEventListener('resize', onWindowResize);

    // Start animation loop
    animate();

    console.log('Three.js viewer initialized successfully');
}

function onWindowResize() {
    const aspect = canvas.clientWidth / canvas.clientHeight;
    camera.aspect = aspect;
    camera.updateProjectionMatrix();
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

// File handling
function setupFileHandling() {
    // Click to upload
    overlay.addEventListener('click', (e) => {
        if (!overlay.classList.contains('has-file')) {
            fileInput.click();
        }
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Drag and drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        canvas.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    canvas.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (file.name.toLowerCase().endsWith('.ifc')) {
                handleFile(file);
            } else {
                alert('Please select a valid IFC file');
            }
        }
    });
}

function handleFile(file) {
    // Update file input
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;

    // Update UI
    placeholder.style.display = 'none';
    fileInfo.style.display = 'block';
    overlay.classList.add('has-file');

    fileNameDisplay.textContent = file.name;
    const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
    fileSizeDisplay.textContent = `Size: ${sizeInMB} MB`;

    console.log('File selected:', file.name);

    // Show a message that 3D loading will be added later
    alert('File uploaded successfully! 3D model display will be enabled in the next update.\n\nFor now, you can proceed with the compliance check.');
}

// Form submission
function setupFormSubmission() {
    document.getElementById('checkForm').addEventListener('submit', async function(e) {
        e.preventDefault();

        const submitBtn = document.getElementById('submitBtn');
        const loading = document.getElementById('loading');
        const result = document.getElementById('result');

        submitBtn.disabled = true;
        loading.style.display = 'block';
        result.style.display = 'none';

        try {
            const formData = new FormData(this);

            const response = await fetch('/check', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Check failed: ${response.statusText}`);
            }

            const complianceResult = await response.json();

            if (!complianceResult || !complianceResult.overall_status) {
                throw new Error('Invalid compliance result');
            }

            const overallStatus = complianceResult.overall_status;
            const isCompliant = overallStatus === 'compliant';
            const isPartial = overallStatus === 'partial';

            let statusText = 'UNKNOWN';
            let statusColor = '#666';
            if (isCompliant) {
                statusText = 'COMPLIANT';
                statusColor = '#28a745';
            } else if (isPartial) {
                statusText = 'PARTIALLY COMPLIANT';
                statusColor = '#ffc107';
            } else if (overallStatus === 'non_compliant') {
                statusText = 'NON-COMPLIANT';
                statusColor = '#dc3545';
            } else if (overallStatus === 'uncertain') {
                statusText = 'UNCERTAIN';
                statusColor = '#6c757d';
            }

            result.className = 'result show ' + (isCompliant ? 'success' : 'error');

            let resultHtml = `
                <h3>Compliance Check Report</h3>

                <div class="report-card">
                    <h4 style="color: ${statusColor}">${statusText}</h4>
                    <p><strong>Total Components:</strong> ${
                        (complianceResult.compliant_components?.length || 0) +
                        (complianceResult.non_compliant_components?.length || 0) +
                        (complianceResult.uncertain_components?.length || 0)
                    }</p>
                    <p style="color: #28a745">✓ Compliant: ${complianceResult.compliant_components?.length || 0}</p>
                    <p style="color: #dc3545">✗ Non-Compliant: ${complianceResult.non_compliant_components?.length || 0}</p>
                    <p style="color: #ffc107">? Uncertain: ${complianceResult.uncertain_components?.length || 0}</p>
                </div>
            `;

            // Show compliant components
            if (complianceResult.compliant_components?.length > 0) {
                resultHtml += `<div class="report-card">
                    <h4 style="color: #28a745">✓ Compliant Components</h4>`;
                complianceResult.compliant_components.forEach(comp => {
                    resultHtml += `
                        <div style="border-left: 4px solid #28a745; padding: 10px; margin: 10px 0; background-color: #f8f9fa;">
                            <strong>${comp.component_type}</strong>
                            <span style="color: #666; font-size: 0.85em;">(ID: ${comp.component_id})</span>
                            <br><small><strong>Rule:</strong> ${comp.checked_rule}</small>
                            <br><small><strong>Data:</strong> ${JSON.stringify(comp.data_used)}</small>
                        </div>
                    `;
                });
                resultHtml += `</div>`;
            }

            // Show non-compliant components
            if (complianceResult.non_compliant_components?.length > 0) {
                resultHtml += `<div class="report-card">
                    <h4 style="color: #dc3545">✗ Non-Compliant Components</h4>`;
                complianceResult.non_compliant_components.forEach(comp => {
                    resultHtml += `
                        <div style="border-left: 4px solid #dc3545; padding: 10px; margin: 10px 0; background-color: #f8f9fa;">
                            <strong>${comp.component_type}</strong>
                            <span style="color: #666; font-size: 0.85em;">(ID: ${comp.component_id})</span>
                            <br><small><strong>Rule:</strong> ${comp.checked_rule}</small>
                            <br><small style="color: #dc3545"><strong>Violation:</strong> ${comp.violation_reason || 'No details'}</small>
                            ${comp.suggested_fix ? `<br><small style="color: #007bff"><strong>Fix:</strong> ${comp.suggested_fix}</small>` : ''}
                            <br><small><strong>Data:</strong> ${JSON.stringify(comp.data_used)}</small>
                        </div>
                    `;
                });
                resultHtml += `</div>`;
            }

            // Show uncertain components
            if (complianceResult.uncertain_components?.length > 0) {
                resultHtml += `<div class="report-card">
                    <h4 style="color: #ffc107">? Uncertain Components</h4>`;
                complianceResult.uncertain_components.forEach(comp => {
                    resultHtml += `
                        <div style="border-left: 4px solid #ffc107; padding: 10px; margin: 10px 0; background-color: #f8f9fa;">
                            <strong>${comp.component_type}</strong>
                            <span style="color: #666; font-size: 0.85em;">(ID: ${comp.component_id})</span>
                            <br><small><strong>Rule:</strong> ${comp.checked_rule}</small>
                            <br><small><strong>Reason:</strong> ${comp.violation_reason || 'Insufficient data'}</small>
                        </div>
                    `;
                });
                resultHtml += `</div>`;
            }

            result.innerHTML = resultHtml;

        } catch (error) {
            result.className = 'result show error';
            result.innerHTML = `<h3>Check Failed</h3><p>Error: ${error.message}</p>`;
        } finally {
            submitBtn.disabled = false;
            loading.style.display = 'none';
        }
    });
}

// Initialize everything
initViewer();
setupFileHandling();
setupFormSubmission();
