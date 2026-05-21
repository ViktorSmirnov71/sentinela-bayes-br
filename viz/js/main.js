// Sentinela — 3D ghost map of Brazilian tailings-dam failure risk.
//
// Renders the per-dam predictions from the hierarchical Bayesian model as
// glowing spikes erupting from the actual SRTM-derived terrain surface of
// Brazil. Aesthetic target: dark, atmospheric, faintly haunted. Visual
// encoding:
//   terrain mesh        SRTM elevation (vertical exaggeration ~70x)
//   spike height        predicted 12-month failure probability
//   spike colour        cyan -> violet -> magenta along risk decile
//   top-30 dams         pulse with stronger glow
//   active emergency    yellow ground halo around the dam

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";

const BRAZIL_BBOX = { lonMin: -75, lonMax: -30, latMin: -35, latMax: 6 };
const PLANE_W = 220;        // world-space width
const PLANE_H = PLANE_W * (BRAZIL_BBOX.latMax - BRAZIL_BBOX.latMin) /
                          (BRAZIL_BBOX.lonMax - BRAZIL_BBOX.lonMin);
const ELEV_TO_WORLD = 0.0025;   // metres of elevation -> world units (=~ 70x exaggeration)
const RISK_SCALE = 1400;        // spike height per unit of predicted probability

// ---------- map projection ----------
// Plate-carrée mapping into a centred plane.
function project(lon, lat) {
  const fx = (lon - BRAZIL_BBOX.lonMin) / (BRAZIL_BBOX.lonMax - BRAZIL_BBOX.lonMin);
  const fy = (lat - BRAZIL_BBOX.latMin) / (BRAZIL_BBOX.latMax - BRAZIL_BBOX.latMin);
  return {
    x: (fx - 0.5) * PLANE_W,
    z: -(fy - 0.5) * PLANE_H,
  };
}

// Light-mode risk ramp: teal -> deep violet -> magenta. Saturated enough to
// pop against the pale background; no glow / bloom needed.
function riskColour(t /* 0..1, higher = riskier */) {
  const c0 = new THREE.Color(0x00a896);
  const c1 = new THREE.Color(0x6b3aa0);
  const c2 = new THREE.Color(0xc8186c);
  if (t < 0.5) return c0.clone().lerp(c1, t * 2);
  return c1.clone().lerp(c2, (t - 0.5) * 2);
}

// ---------- scene setup ----------
const app = document.getElementById("app");
const tooltip = document.getElementById("tooltip");

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf4f6f9);
scene.fog = new THREE.FogExp2(0xf4f6f9, 0.0055);

const camera = new THREE.PerspectiveCamera(
  42, window.innerWidth / window.innerHeight, 0.1, 1200
);
camera.position.set(70, 90, 140);

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.NoToneMapping;
renderer.toneMappingExposure = 1.0;
app.appendChild(renderer.domElement);

// Very mild bloom — just enough to give the saturated spike tips a soft halo
// against the pale background; not the heavy glow of the dark version.
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight),
  /* strength */ 0.22, /* radius */ 0.55, /* threshold */ 0.55
));

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.target.set(0, 4, 0);
controls.maxPolarAngle = Math.PI * 0.48;
controls.minDistance = 30;
controls.maxDistance = 320;

// ---------- async load all data ----------
const [terrain, dams, summary, outline] = await Promise.all([
  fetch("./data/terrain.json").then(r => r.json()),
  fetch("./data/dams.json").then(r => r.json()),
  fetch("./data/summary.json").then(r => r.json()),
  fetch("./data/brazil_outline.json").then(r => r.json()),
]);

document.getElementById("stat-n").textContent = dams.length;
document.getElementById("stat-max").textContent = (summary.max_risk * 100).toFixed(3) + "%";
document.getElementById("stat-snap").textContent = summary.snapshot_month;

// ---------- TERRAIN MESH ----------
// PlaneGeometry sits in the XY plane until we rotate it onto the XZ plane.
const TW = terrain.width, TH = terrain.height;
const terrainGeo = new THREE.PlaneGeometry(PLANE_W, PLANE_H, TW - 1, TH - 1);
terrainGeo.rotateX(-Math.PI / 2);   // lay it flat so +Y is up

// Displace each vertex by its elevation.
const elev = terrain.elevation_m;
const positions = terrainGeo.attributes.position;
// We will also build a per-vertex colour array so high points read brighter.
const colours = new Float32Array(positions.count * 3);

const elevMin = terrain.elev_min_m;
const elevMax = terrain.elev_max_m;

for (let i = 0; i < positions.count; i++) {
  const e = elev[i];
  const y = e * ELEV_TO_WORLD;
  positions.setY(i, y);
  // Light-mode terrain palette: pale grey-blue lowland -> slightly warmer
  // tan-grey highland. Subtle enough to remain background; rich enough to
  // reveal Brazilian highland structure.
  const t = Math.min(1, Math.max(0, (e - elevMin) / (elevMax - elevMin + 1e-6)));
  const r = 0.84 + 0.05 * t;
  const g = 0.86 + 0.02 * t;
  const b = 0.88 - 0.10 * t;
  colours[i * 3 + 0] = r;
  colours[i * 3 + 1] = g;
  colours[i * 3 + 2] = b;
}
positions.needsUpdate = true;
terrainGeo.computeVertexNormals();
terrainGeo.setAttribute("color", new THREE.BufferAttribute(colours, 3));

const terrainMat = new THREE.MeshStandardMaterial({
  vertexColors: true,
  flatShading: true,
  metalness: 0.0,
  roughness: 1.0,
  transparent: false,
});
const terrainMesh = new THREE.Mesh(terrainGeo, terrainMat);
scene.add(terrainMesh);

// Topographic wireframe overlay — darker grey for legibility on a light bg.
const wireGeo = terrainGeo.clone();
const wireMat = new THREE.MeshBasicMaterial({
  color: 0x5a6878,
  wireframe: true,
  transparent: true,
  opacity: 0.10,
  depthWrite: false,
});
const wireMesh = new THREE.Mesh(wireGeo, wireMat);
wireMesh.position.y = 0.04;
scene.add(wireMesh);

// Helper: sample interpolated terrain elevation in world units at a (lon, lat).
function sampleTerrainY(lon, lat) {
  const fx = (lon - BRAZIL_BBOX.lonMin) / (BRAZIL_BBOX.lonMax - BRAZIL_BBOX.lonMin) * (TW - 1);
  const fy = (BRAZIL_BBOX.latMax - lat) / (BRAZIL_BBOX.latMax - BRAZIL_BBOX.latMin) * (TH - 1);
  const x0 = Math.max(0, Math.min(TW - 1, Math.floor(fx)));
  const y0 = Math.max(0, Math.min(TH - 1, Math.floor(fy)));
  const x1 = Math.min(TW - 1, x0 + 1);
  const y1 = Math.min(TH - 1, y0 + 1);
  const dx = fx - x0, dy = fy - y0;
  const e =
    elev[y0 * TW + x0] * (1 - dx) * (1 - dy) +
    elev[y0 * TW + x1] * dx * (1 - dy) +
    elev[y1 * TW + x0] * (1 - dx) * dy +
    elev[y1 * TW + x1] * dx * dy;
  return e * ELEV_TO_WORLD;
}

// ---------- Brazil outline (sits above the terrain) ----------
{
  const coords = outline.features[0].geometry.coordinates[0];
  const pts = coords.map(([lon, lat]) => {
    const { x, z } = project(lon, lat);
    const y = sampleTerrainY(lon, lat) + 0.4;
    return new THREE.Vector3(x, y, z);
  });
  const geom = new THREE.BufferGeometry().setFromPoints(pts);
  const mat = new THREE.LineBasicMaterial({
    color: 0x1d6cff, transparent: true, opacity: 0.85, linewidth: 2,
  });
  scene.add(new THREE.Line(geom, mat));
}

// ---------- spikes ----------
const maxRisk = summary.max_risk;
const top30Set = new Set(dams.slice(0, 30).map(d => d.dam_id));

const pillarsGroup = new THREE.Group();
scene.add(pillarsGroup);

// Use a single cone geometry for all spikes; instancing would be faster but
// 877 individual meshes is fine on any GPU.
const spikeGeo = new THREE.ConeGeometry(0.28, 1.0, 6, 1, false);
spikeGeo.translate(0, 0.5, 0); // base at y=0, tip at y=1

const pillarRecords = [];

for (const dam of dams) {
  const { x, z } = project(dam.lon, dam.lat);
  const tRisk = Math.pow(dam.risk_12m / maxRisk, 0.45);  // gamma curve
  const spikeHeight = Math.max(0.6, dam.risk_12m * RISK_SCALE);
  const colour = riskColour(tRisk);
  const groundY = sampleTerrainY(dam.lon, dam.lat);

  const mat = new THREE.MeshStandardMaterial({
    color: colour,
    emissive: colour,
    emissiveIntensity: 0.15 + 0.6 * tRisk,   // subtle glow on high-risk only
    roughness: 0.35,
    metalness: 0.05,
  });
  const mesh = new THREE.Mesh(spikeGeo, mat);
  mesh.position.set(x, groundY, z);
  mesh.scale.set(1, spikeHeight, 1);
  mesh.userData = { dam };
  pillarsGroup.add(mesh);

  pillarRecords.push({
    mesh, dam, baseHeight: spikeHeight, groundY,
    isTop30: top30Set.has(dam.dam_id),
  });

  // Emergency-level halo (ring on the ground at the dam's elevation).
  if (dam.emergency_level >= 1) {
    const halo = new THREE.Mesh(
      new THREE.RingGeometry(0.9, 1.9, 32),
      new THREE.MeshBasicMaterial({
        color: 0xf59e0b, transparent: true, opacity: 0.85, side: THREE.DoubleSide,
      })
    );
    halo.rotation.x = -Math.PI / 2;
    halo.position.set(x, groundY + 0.08, z);
    pillarsGroup.add(halo);
  }
}

// ---------- lighting (light scene) ----------
scene.add(new THREE.AmbientLight(0xffffff, 0.95));
scene.add(new THREE.HemisphereLight(0xffffff, 0xc8d2dc, 0.45));
const dir = new THREE.DirectionalLight(0xffffff, 0.75);
dir.position.set(-80, 120, 60);
scene.add(dir);
const dirFill = new THREE.DirectionalLight(0xe6ecf3, 0.25);
dirFill.position.set(60, 50, -40);
scene.add(dirFill);

// ---------- atmospheric dust (very subtle in light mode) ----------
{
  const N = 600;
  const positions = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    positions[3 * i + 0] = (Math.random() - 0.5) * PLANE_W * 1.2;
    positions[3 * i + 1] = Math.random() * 50 + 1;
    positions[3 * i + 2] = (Math.random() - 0.5) * PLANE_H * 1.2;
  }
  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const mat = new THREE.PointsMaterial({
    color: 0x8090a0, size: 0.18, transparent: true, opacity: 0.22, depthWrite: false,
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
  const spikeHit = hits.find(h => h.object.userData.dam);
  if (spikeHit) {
    const m = spikeHit.object;
    if (hovered !== m) {
      if (hovered) hovered.material.emissiveIntensity = hovered.userData._rest;
      hovered = m;
      hovered.userData._rest = m.material.emissiveIntensity;
      m.material.emissiveIntensity *= 1.7;
    }
    const d = m.userData.dam;
    tooltip.innerHTML = `
      <div class="name">${escapeHtml(d.name)}</div>
      <div>${escapeHtml(d.operator)}</div>
      <div>${d.state} · ${escapeHtml(d.municipality)} · elev ${d.terrain_elevation_m.toFixed(0)} m</div>
      <div>${d.construction_method} · ${d.ore_type} · h=${d.height_m?.toFixed(0) ?? "?"} m</div>
      <div>CRI ${d.cri ?? "?"} · DPA ${d.dpa ?? "?"} · emergency ${d.emergency_level}</div>
      <div class="risk">12-month risk: ${(d.risk_12m * 100).toFixed(3)}%</div>
    `;
    tooltip.style.display = "block";
    tooltip.style.left = (event.clientX + 14) + "px";
    tooltip.style.top = (event.clientY + 14) + "px";
  } else {
    if (hovered) {
      hovered.material.emissiveIntensity = hovered.userData._rest;
      hovered = null;
    }
    tooltip.style.display = "none";
  }
});

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

// ---------- simulation loop ----------
const clock = new THREE.Clock();
let simT = 0;
const simSpeed = 1 / 90;

function animate() {
  const dt = clock.getDelta();
  simT = (simT + dt * simSpeed) % 1;
  document.getElementById("stat-t").textContent = `month +${Math.floor(simT * 12)} / 12`;

  const pulseBase = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(clock.elapsedTime * 1.8));
  for (const r of pillarRecords) {
    if (r.isTop30) {
      const s = 1.0 + 0.32 * pulseBase;
      r.mesh.scale.y = r.baseHeight * s;
      r.mesh.material.emissiveIntensity = 0.25 + 0.6 * pulseBase;
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
