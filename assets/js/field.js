/* ============================================
   "Mesh field" background (Three.js, self-hosted).
   A 3D field of IoT nodes wired into a mesh network: packets route
   node to node along the links, gateways glow copper, and a
   telemetry wave surface breathes underneath. Mouse adds parallax,
   scrolling moves the camera through the field.
   Loaded after the page is idle; paused when the tab is hidden;
   a single static frame under prefers-reduced-motion.
   ============================================ */

import * as THREE from '../vendor/three.module.min.js';

const TEAL = new THREE.Color('#5fd4be');
const COPPER = new THREE.Color('#d69a66');
const INK = new THREE.Color('#9aa8a4');
const BG = new THREE.Color('#0d1315');

export function startField(container, { reduceMotion = false } = {}) {
    const small = window.innerWidth < 760;
    const NODE_COUNT = small ? 70 : 150;
    const PACKET_COUNT = small ? 14 : 30;
    const LINKS_PER_NODE = 2;

    let renderer;
    try {
        renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'low-power' });
    } catch (e) {
        return null; // No WebGL: the CSS grid background stays.
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(BG, 30, 110);
    const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 300);
    camera.position.set(0, 4, 42);

    // Deterministic PRNG so the layout is the same on every visit.
    let seed = 20260929;
    const rand = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);

    // ---- Nodes ----
    const base = [];
    const gateway = [];
    for (let i = 0; i < NODE_COUNT; i++) {
        base.push(new THREE.Vector3((rand() - 0.5) * 120, (rand() - 0.5) * 46 + 2, -rand() * 70 + 6));
        gateway.push(rand() < 0.08);
    }
    const nodePos = new Float32Array(NODE_COUNT * 3);
    const nodeCol = new Float32Array(NODE_COUNT * 3);
    const nodeSize = new Float32Array(NODE_COUNT);
    base.forEach((p, i) => {
        nodePos.set([p.x, p.y, p.z], i * 3);
        const c = gateway[i] ? COPPER : (rand() < 0.35 ? TEAL : INK);
        nodeCol.set([c.r, c.g, c.b], i * 3);
        nodeSize[i] = gateway[i] ? 5.5 : 2.2 + rand() * 1.6;
    });
    const nodeGeom = new THREE.BufferGeometry();
    nodeGeom.setAttribute('position', new THREE.BufferAttribute(nodePos, 3));
    nodeGeom.setAttribute('color', new THREE.BufferAttribute(nodeCol, 3));
    nodeGeom.setAttribute('size', new THREE.BufferAttribute(nodeSize, 1));

    // Round, soft points with per-vertex size and fog.
    const pointMaterial = (opacity) => new THREE.ShaderMaterial({
        uniforms: {
            uOpacity: { value: opacity },
            uPixelRatio: { value: renderer.getPixelRatio() },
            fogColor: { value: scene.fog.color },
            fogNear: { value: scene.fog.near },
            fogFar: { value: scene.fog.far },
        },
        vertexShader: `
            attribute float size;
            attribute vec3 color;
            varying vec3 vColor;
            varying float vFog;
            uniform float uPixelRatio;
            uniform float fogNear;
            uniform float fogFar;
            void main() {
                vColor = color;
                vec4 mv = modelViewMatrix * vec4(position, 1.0);
                gl_PointSize = size * uPixelRatio * (200.0 / -mv.z);
                vFog = smoothstep(fogNear, fogFar, -mv.z);
                gl_Position = projectionMatrix * mv;
            }`,
        fragmentShader: `
            varying vec3 vColor;
            varying float vFog;
            uniform float uOpacity;
            void main() {
                float d = length(gl_PointCoord - 0.5);
                float a = smoothstep(0.5, 0.0, d);
                a = a * a;
                gl_FragColor = vec4(vColor, a * uOpacity * (1.0 - vFog));
            }`,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
    });
    const nodes = new THREE.Points(nodeGeom, pointMaterial(0.9));
    scene.add(nodes);

    // ---- Links: each node to its nearest neighbours (a mesh network) ----
    const edges = [];
    const adjacency = base.map(() => []);
    const seen = new Set();
    base.forEach((p, i) => {
        const nearest = base
            .map((q, j) => ({ j, d: i === j ? Infinity : p.distanceToSquared(q) }))
            .sort((a, b) => a.d - b.d)
            .slice(0, LINKS_PER_NODE);
        nearest.forEach(({ j }) => {
            const key = i < j ? i + ':' + j : j + ':' + i;
            if (seen.has(key)) return;
            seen.add(key);
            edges.push([i, j]);
            adjacency[i].push(j);
            adjacency[j].push(i);
        });
    });
    const linkPos = new Float32Array(edges.length * 6);
    const linkGeom = new THREE.BufferGeometry();
    linkGeom.setAttribute('position', new THREE.BufferAttribute(linkPos, 3));
    const links = new THREE.LineSegments(linkGeom, new THREE.LineBasicMaterial({
        color: TEAL, transparent: true, opacity: 0.16, fog: true, depthWrite: false,
    }));
    scene.add(links);

    // ---- Packets: random walk along the mesh, like routed messages ----
    const packets = [];
    const packetPos = new Float32Array(PACKET_COUNT * 3);
    const packetCol = new Float32Array(PACKET_COUNT * 3);
    const packetSize = new Float32Array(PACKET_COUNT);
    for (let k = 0; k < PACKET_COUNT; k++) {
        const from = Math.floor(rand() * NODE_COUNT);
        const next = adjacency[from].length ? adjacency[from][Math.floor(rand() * adjacency[from].length)] : from;
        packets.push({ from, to: next, t: rand(), speed: 0.25 + rand() * 0.45 });
        const c = k % 4 === 0 ? COPPER : TEAL;
        packetCol.set([c.r * 1.3, c.g * 1.3, c.b * 1.3], k * 3);
        packetSize[k] = 4.2;
    }
    const packetGeom = new THREE.BufferGeometry();
    packetGeom.setAttribute('position', new THREE.BufferAttribute(packetPos, 3));
    packetGeom.setAttribute('color', new THREE.BufferAttribute(packetCol, 3));
    packetGeom.setAttribute('size', new THREE.BufferAttribute(packetSize, 1));
    scene.add(new THREE.Points(packetGeom, pointMaterial(1)));

    // ---- Telemetry wave surface ----
    const plane = new THREE.PlaneGeometry(220, 120, small ? 40 : 70, small ? 22 : 36);
    plane.rotateX(-Math.PI / 2);
    const planeBase = plane.attributes.position.array.slice();
    const surfacePoints = new THREE.Points(plane, new THREE.PointsMaterial({
        color: COPPER, size: 0.2, transparent: true, opacity: 0.22, fog: true, depthWrite: false,
    }));
    surfacePoints.position.set(0, -30, -40);
    scene.add(surfacePoints);

    // ---- Interaction ----
    const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
    let scrollP = 0;
    const onPointer = (e) => {
        pointer.tx = (e.clientX / window.innerWidth - 0.5) * 2;
        pointer.ty = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    const onScroll = () => {
        const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
        scrollP = window.scrollY / max;
    };
    const onResize = () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('pointermove', onPointer, { passive: true });
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onResize);
    onScroll();

    // ---- Frame ----
    const clock = new THREE.Clock();
    const cur = new Array(NODE_COUNT);
    for (let i = 0; i < NODE_COUNT; i++) cur[i] = new THREE.Vector3();

    function update(time, dt) {
        // Nodes drift gently around their base positions.
        for (let i = 0; i < NODE_COUNT; i++) {
            const b = base[i];
            cur[i].set(
                b.x + Math.sin(time * 0.21 + i) * 0.9,
                b.y + Math.cos(time * 0.17 + i * 1.3) * 0.8,
                b.z + Math.sin(time * 0.13 + i * 0.7) * 0.9
            );
            nodePos[i * 3] = cur[i].x; nodePos[i * 3 + 1] = cur[i].y; nodePos[i * 3 + 2] = cur[i].z;
            if (gateway[i]) nodeSize[i] = 5.5 + Math.sin(time * 2 + i) * 1.4;
        }
        nodeGeom.attributes.position.needsUpdate = true;
        nodeGeom.attributes.size.needsUpdate = true;

        for (let e = 0, o = 0; e < edges.length; e++, o += 6) {
            const a = cur[edges[e][0]], b = cur[edges[e][1]];
            linkPos[o] = a.x; linkPos[o + 1] = a.y; linkPos[o + 2] = a.z;
            linkPos[o + 3] = b.x; linkPos[o + 4] = b.y; linkPos[o + 5] = b.z;
        }
        linkGeom.attributes.position.needsUpdate = true;

        packets.forEach((p, k) => {
            p.t += dt * p.speed;
            if (p.t >= 1) {
                p.t -= 1;
                const options = adjacency[p.to].filter((n) => n !== p.from);
                p.from = p.to;
                const pool = options.length ? options : adjacency[p.to];
                p.to = pool.length ? pool[Math.floor(rand() * pool.length)] : p.from;
            }
            const a = cur[p.from], b = cur[p.to];
            packetPos[k * 3] = a.x + (b.x - a.x) * p.t;
            packetPos[k * 3 + 1] = a.y + (b.y - a.y) * p.t;
            packetPos[k * 3 + 2] = a.z + (b.z - a.z) * p.t;
        });
        packetGeom.attributes.position.needsUpdate = true;

        const arr = plane.attributes.position.array;
        for (let v = 0; v < arr.length; v += 3) {
            const x = planeBase[v], z = planeBase[v + 2];
            arr[v + 1] = Math.sin(x * 0.06 + time * 0.6) * 1.6 + Math.cos(z * 0.08 + time * 0.4) * 1.2;
        }
        plane.attributes.position.needsUpdate = true;

        // Camera: mouse parallax + a slow dolly through the field on scroll.
        pointer.x += (pointer.tx - pointer.x) * 0.04;
        pointer.y += (pointer.ty - pointer.y) * 0.04;
        camera.position.x = pointer.x * 4;
        camera.position.y = 4 - pointer.y * 2.5 - scrollP * 4;
        camera.position.z = 42 - scrollP * 18;
        camera.lookAt(0, -scrollP * 3, -20);
        scene.rotation.y = Math.sin(time * 0.03) * 0.08 + scrollP * 0.35;
    }

    let running = false;
    let raf = 0;
    function loop() {
        raf = requestAnimationFrame(loop);
        const dt = Math.min(clock.getDelta(), 0.05);
        update(clock.elapsedTime, dt);
        renderer.render(scene, camera);
    }
    function start() { if (!running && !reduceMotion && !document.hidden) { running = true; clock.getDelta(); loop(); } }
    function stop() { running = false; cancelAnimationFrame(raf); }

    update(4, 0);
    renderer.render(scene, camera);
    container.classList.add('ready');
    // Static frame under reduced motion (re-rendered on resize); follows live changes.
    window.addEventListener('resize', () => { if (!running) renderer.render(scene, camera); });
    document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onMotionChange = (e) => { reduceMotion = e.matches; if (reduceMotion) stop(); else start(); };
    if (motionQuery.addEventListener) motionQuery.addEventListener('change', onMotionChange);
    start();
    return { start, stop };
}
