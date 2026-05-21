// Sentinela — 3D ghost map of Brazilian tailings-dam failure risk.
//
// Renders the per-dam predictions from the hierarchical Bayesian model as
// glowing pillars over a simplified Brazil silhouette. Aesthetic target:
// dark, atmospheric, faintly haunted. Visual encoding:
//   pillar height  = predicted 12-month failure probability
//   pillar colour  = risk decile (cyan -> violet -> magenta)
//   top-30 dams    = pulse animation, larger glow
//   active emergency dams = yellow halo

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass }     from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";

const BRAZIL_BBOX = { lonMin: -75, lonMax: -30, latMin: -35, latMax: 6 };
const PLANE_SIZE = 200;     // world-space units
const RISK_SCALE = 1200;    // pillar height per unit probability

// ---------- map projection ----------
// Plate-carrée mapping from (lon, lat) into a centred plane.
function project(lon, lat) {
  const lonSpan = BRAZIL_BBOX.lonMax - BRAZIL_BBOX.lonMin;
  const latSpan = BRAZIL_BBOX.latMax - BRAZIL_BBOX.latMin;
  const x =  ((lon - BRAZIL_BBOX.lonMin) / lonSpan - 0.5) * PLANE_SIZE;
  const z = -((lat - BRAZIL_BBOX.latMin) / latSpan - 0.5) * PLANE_SIZE;
  return { x, z };
}

// ---------- colour ramp ----------
function riskColour(t /* 0..1, higher = riskier */) {
  // cyan (#5cffe0) -> violet (#a07cff) -> magenta (#ff5cc8)
  const c0 = new THREE.Color(0x5cffe0);
  const c1 = new THREE.Color(0xa07cff);
  const c2 = new THREE.Color(0xff5cc8);
  if (t < 0.5) return c0.clone().lerp(c1, t * 2);
  return c1.clone().lerp(c2, (t - 0.5) * 2);
}

// ---------- scene setup ----------
const app = document.getElementById("app");
const tooltip = document.getElementById("tooltip");

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x03060c);
scene.fog = new THREE.FogExp2(0x03060c, 0.012);

const camera = new THREE.PerspectiveCamera(
  45, window.innerWidth / window.innerHeight, 0.1, 800
);
camera.position.set(60, 110, 130);

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.85;
app.appendChild(renderer.domElement);

// Post-processing: bloom for the ghostly neon glow.
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight),
  /* strength */ 1.1, /* radius */ 0.7, /* threshold */ 0.0
));

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.target.set(0, 0, 0);
controls.maxPolarAngle = Math.PI * 0.49;
controls.minDistance = 30;
controls.maxDistance = 280;

// ---------- ground plane (Brazil silhouette + grid + radial fade) ----------
const groundGroup = new THREE.Group();
scene.add(groundGroup);

// Subtle base disc just to anchor depth perception.
const baseDisc = new THREE.Mesh(
  new THREE.CircleGeometry(PLANE_SIZE * 0.95, 96),
  new THREE.MeshBasicMaterial({
    color: 0x0b1622,
    transparent: true,
    opacity: 0.6,
    side: THREE.DoubleSide,
  })
);
baseDisc.rotation.x = -Math.PI / 2;
baseDisc.position.y = -0.01;
groundGroup.add(baseDisc);

// Grid for the spatial reference.
const grid = new THREE.GridHelper(PLANE_SIZE, 30, 0x1c324a, 0x0f1e30);
grid.material.transparent = true;
grid.material.opacity = 0.35;
grid.position.y = 0;
groundGroup.add(grid);

// ---------- load data ----------
const [dams, summary, outline] = await Promise.all([
  fetch("./data/dams.json").then(r => r.json()),
  fetch("./data/summary.json").then(r => r.json()),
  fetch("./data/brazil_outline.json").then(r => r.json()),
]);

document.getElementById("stat-n").textContent = dams.length;
document.getElementById("stat-max").textContent = (summary.max_risk * 100).toFixed(3) + "%";
document.getElementById("stat-snap").textContent = summary.snapshot_month;

// ---------- Brazil outline (extruded ribbon) ----------
{
  const coords = outline.features[0].geometry.coordinates[0];
  const pts = coords.map(([lon, lat]) => {
    const { x, z } = project(lon, lat);
    return new THREE.Vector3(x, 0.05, z);
  });
  const geom = new THREE.BufferGeometry().setFromPoints(pts);
  const mat = new THREE.LineBasicMaterial({ color: 0x4ef0c0, transparent: true, opacity: 0.65 });
  groundGroup.add(new THREE.Line(geom, mat));

  // A second offset copy gives a faint double-stroke "halo" effect.
  const mat2 = new THREE.LineBasicMaterial({ color: 0x88e6ff, transparent: true, opacity: 0.18 });
  const halo = new THREE.Line(geom.clone(), mat2);
  halo.position.y = 0.5;
  groundGroup.add(halo);
}

// ---------- pillars ----------
const maxRisk = summary.max_risk;
const riskDecileThreshold = (() => {
  const sorted = [...dams].sort((a, b) => b.risk_12m - a.risk_12m);
  return sorted[Math.floor(sorted.length * 0.1)]?.risk_12m ?? 0;
})();
const top30Set = new Set(dams.slice(0, 30).map(d => d.dam_id));

const pillarsGroup = new THREE.Group();
scene.add(pillarsGroup);

const pillarRecords = [];   // { mesh, dam, baseHeight, isTop30 }
const damGeometry = new THREE.CylinderGeometry(0.3, 0.3, 1, 6);

for (const dam of dams) {
  const { x, z } = project(dam.lon, dam.lat);
  const tRisk = Math.pow(dam.risk_12m / maxRisk, 0.45);   // gamma-curve for visibility
  const height = Math.max(0.5, dam.risk_12m * RISK_SCALE);
  const colour = riskColour(tRisk);

  const mat = new THREE.MeshStandardMaterial({
    color: colour,
    emissive: colour,
    emissiveIntensity: 1.6 + 3 * tRisk,
    roughness: 0.3,
    metalness: 0.15,
    transparent: true,
    opacity: 0.92,
  });
  const mesh = new THREE.Mesh(damGeometry, mat);
  mesh.position.set(x, height / 2, z);
  mesh.scale.set(1, height, 1);
  mesh.userData = { dam };
  pillarsGroup.add(mesh);

  pillarRecords.push({
    mesh,
    dam,
    baseHeight: height,
    isTop30: top30Set.has(dam.dam_id),
    isEmergency: dam.emergency_level >= 1,
  });

  // Emergency-level halo (yellow point-light + glow disc on the ground).
  if (dam.emergency_level >= 1) {
    const halo = new THREE.Mesh(
      new THREE.CircleGeometry(1.6, 24),
      new THREE.MeshBasicMaterial({
        color: 0xffe97c, transparent: true, opacity: 0.35, side: THREE.DoubleSide,
      })
    );
    halo.rotation.x = -Math.PI / 2;
    halo.position.set(x, 0.06, z);
    groundGroup.add(halo);
  }
}

// ---------- lighting ----------
const ambient = new THREE.AmbientLight(0x142840, 0.6);
scene.add(ambient);
const hemi = new THREE.HemisphereLight(0x88e6ff, 0x06080c, 0.4);
scene.add(hemi);

// ---------- particles ("ghost dust") ----------
{
  const N = 1200;
  const positions = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    positions[3*i + 0] = (Math.random() - 0.5) * PLANE_SIZE * 1.4;
    positions[3*i + 1] = Math.random() * 60 + 0.5;
    positions[3*i + 2] = (Math.random() - 0.5) * PLANE_SIZE * 1.4;
  }
  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const mat = new THREE.PointsMaterial({
    color: 0x88e6ff,
    size: 0.4,
    transparent: true,
    opacity: 0.4,
    depthWrite: false,
  });
  scene.add(new THREE.Points(geom, mat));
}

// ---------- raycaster for tooltip ----------
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
let hovered = null;

window.addEventListener("mousemove", (event) => {
  mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
  mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
  raycaster.setFromCamera(mouse, camera);
  const hits = raycaster.intersectObjects(pillarsGroup.children, false);
  if (hits.length > 0) {
    const m = hits[0].object;
    if (hovered !== m) {
      if (hovered) hovered.material.emissiveIntensity = hovered.userData.dam._restEmissive;
      hovered = m;
      hovered.userData.dam._restEmissive = m.material.emissiveIntensity;
      m.material.emissiveIntensity *= 1.6;
    }
    const d = m.userData.dam;
    tooltip.innerHTML = `
      <div class="name">${escapeHtml(d.name)}</div>
      <div>${escapeHtml(d.operator)}</div>
      <div>${d.state} · ${escapeHtml(d.municipality)}</div>
      <div>${d.construction_method} · ${d.ore_type} · h=${d.height_m?.toFixed(0) ?? "?"} m</div>
      <div>CRI ${d.cri ?? "?"} · DPA ${d.dpa ?? "?"} · emergency ${d.emergency_level}</div>
      <div class="risk">12-month risk: ${(d.risk_12m * 100).toFixed(3)}%</div>
    `;
    tooltip.style.display = "block";
    tooltip.style.left = (event.clientX + 14) + "px";
    tooltip.style.top  = (event.clientY + 14) + "px";
  } else {
    if (hovered) {
      hovered.material.emissiveIntensity = hovered.userData.dam._restEmissive;
      hovered = null;
    }
    tooltip.style.display = "none";
  }
});

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

// ---------- simulation loop ----------
// "Simulation t" represents a slow forward sweep through hypothetical months
// of risk evolution; the highest-risk dams pulse stronger as t cycles.

const clock = new THREE.Clock();
let simT = 0;
const simSpeed = 1 / 90;   // one full simulated month per ~90 real seconds

function animate() {
  const dt = clock.getDelta();
  simT = (simT + dt * simSpeed) % 1;
  document.getElementById("stat-t").textContent =
    `month +${Math.floor(simT * 12)} / 12`;

  const pulseBase = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(clock.elapsedTime * 1.8));

  for (const r of pillarRecords) {
    if (r.isTop30) {
      // Pulse top-30: scale Y and emissive intensity.
      const s = 1.0 + 0.4 * pulseBase;
      r.mesh.scale.y = r.baseHeight * s;
      r.mesh.position.y = (r.baseHeight * s) / 2;
      r.mesh.material.emissiveIntensity = 2.5 + 4 * pulseBase;
    }
  }

  controls.update();
  composer.render();
  requestAnimationFrame(animate);
}
animate();

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  composer.setSize(window.innerWidth, window.innerHeight);
});
