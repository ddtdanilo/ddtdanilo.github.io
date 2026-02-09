/* ============================================
   DANILO DÍAZ TARASCÓ — Portfolio JS
   Three.js 3D Background + GSAP Animations
   + i18n (EN/ES) with auto-detection
   ============================================ */

(function () {
    'use strict';

    // ---- i18n System ----
    var currentLang = 'en';

    function detectLanguage() {
        // Check localStorage first
        var saved = localStorage.getItem('ddt-lang');
        if (saved === 'en' || saved === 'es') return saved;

        // Auto-detect from browser language
        var browserLang = (navigator.language || navigator.userLanguage || 'en').toLowerCase();
        if (browserLang.startsWith('es')) return 'es';
        return 'en';
    }

    function setLanguage(lang) {
        currentLang = lang;
        localStorage.setItem('ddt-lang', lang);
        document.documentElement.lang = lang;

        // Update all translatable elements
        document.querySelectorAll('[data-' + lang + ']').forEach(function (el) {
            var text = el.getAttribute('data-' + lang);
            if (text) el.innerHTML = text;
        });

        // Update toggle UI
        document.querySelectorAll('.lang-option').forEach(function (opt) {
            opt.classList.toggle('active', opt.getAttribute('data-lang') === lang);
        });
    }

    function initLanguage() {
        var detected = detectLanguage();
        setLanguage(detected);

        var toggle = document.getElementById('lang-toggle');
        if (toggle) {
            toggle.addEventListener('click', function () {
                setLanguage(currentLang === 'en' ? 'es' : 'en');
            });
        }
    }

    // ---- Three.js 3D Scene ----
    var canvasContainer = document.getElementById('canvas-container');
    var scene, camera, renderer, particles, geometries = [];
    var mouseX = 0, mouseY = 0;
    var windowW = window.innerWidth;
    var windowH = window.innerHeight;

    function initThree() {
        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(75, windowW / windowH, 0.1, 1000);
        camera.position.z = 30;

        renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
        renderer.setSize(windowW, windowH);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        canvasContainer.appendChild(renderer.domElement);

        // Particle field
        var particleCount = Math.min(1500, Math.floor(windowW * 0.8));
        var positions = new Float32Array(particleCount * 3);
        var colors = new Float32Array(particleCount * 3);

        for (var i = 0; i < particleCount; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 80;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 80;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 80;

            var t = Math.random();
            colors[i * 3] = t * 0 + (1 - t) * 0.48;
            colors[i * 3 + 1] = t * 0.83 + (1 - t) * 0.38;
            colors[i * 3 + 2] = t * 1 + (1 - t) * 1;
        }

        var particleGeom = new THREE.BufferGeometry();
        particleGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        particleGeom.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        var particleMat = new THREE.PointsMaterial({
            size: 0.08,
            vertexColors: true,
            transparent: true,
            opacity: 0.7,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        particles = new THREE.Points(particleGeom, particleMat);
        scene.add(particles);

        // Floating wireframe geometries
        var geoTypes = [
            new THREE.IcosahedronGeometry(3, 1),
            new THREE.OctahedronGeometry(2.5, 0),
            new THREE.TorusGeometry(2, 0.6, 8, 16),
            new THREE.TetrahedronGeometry(2, 0),
        ];

        var geoPositions = [
            { x: -15, y: 8, z: -10 },
            { x: 18, y: -6, z: -15 },
            { x: -10, y: -12, z: -8 },
            { x: 14, y: 10, z: -20 },
        ];

        geoTypes.forEach(function (geo, i) {
            var mat = new THREE.MeshBasicMaterial({
                color: i % 2 === 0 ? 0x00d4ff : 0x7b61ff,
                wireframe: true,
                transparent: true,
                opacity: 0.15,
            });
            var mesh = new THREE.Mesh(geo, mat);
            mesh.position.set(geoPositions[i].x, geoPositions[i].y, geoPositions[i].z);
            mesh.userData = {
                rotSpeed: { x: 0.002 + Math.random() * 0.005, y: 0.003 + Math.random() * 0.005 },
                floatOffset: Math.random() * Math.PI * 2,
                baseY: geoPositions[i].y,
            };
            geometries.push(mesh);
            scene.add(mesh);
        });
    }

    function animateThree() {
        requestAnimationFrame(animateThree);
        var time = Date.now() * 0.001;

        if (particles) {
            particles.rotation.x += 0.0003;
            particles.rotation.y += 0.0005;
            particles.rotation.x += (mouseY * 0.0001 - particles.rotation.x * 0.01);
            particles.rotation.y += (mouseX * 0.0001 - particles.rotation.y * 0.01);
        }

        geometries.forEach(function (mesh) {
            mesh.rotation.x += mesh.userData.rotSpeed.x;
            mesh.rotation.y += mesh.userData.rotSpeed.y;
            mesh.position.y = mesh.userData.baseY + Math.sin(time + mesh.userData.floatOffset) * 1.5;
        });

        renderer.render(scene, camera);
    }

    // ---- Custom Cursor ----
    function initCursor() {
        var cursor = document.getElementById('cursor');
        var follower = document.getElementById('cursor-follower');
        if (!cursor || !follower) return;

        if ('ontouchstart' in window) {
            cursor.style.display = 'none';
            follower.style.display = 'none';
            return;
        }

        var cx = 0, cy = 0;
        var fx = 0, fy = 0;

        document.addEventListener('mousemove', function (e) {
            mouseX = e.clientX - windowW / 2;
            mouseY = e.clientY - windowH / 2;
            cx = e.clientX;
            cy = e.clientY;
        });

        function updateCursor() {
            fx += (cx - fx) * 0.12;
            fy += (cy - fy) * 0.12;
            cursor.style.left = cx + 'px';
            cursor.style.top = cy + 'px';
            follower.style.left = fx + 'px';
            follower.style.top = fy + 'px';
            requestAnimationFrame(updateCursor);
        }
        updateCursor();

        var hoverElements = document.querySelectorAll('a, button, .skill-card, .project-item');
        hoverElements.forEach(function (el) {
            el.addEventListener('mouseenter', function () { follower.classList.add('hover'); });
            el.addEventListener('mouseleave', function () { follower.classList.remove('hover'); });
        });
    }

    // ---- Loader ----
    function initLoader() {
        var progress = document.querySelector('.loader-progress');
        var loader = document.getElementById('loader');
        var pct = 0;

        var loadInterval = setInterval(function () {
            pct += Math.random() * 15 + 5;
            if (pct >= 100) {
                pct = 100;
                clearInterval(loadInterval);
                progress.style.width = '100%';
                setTimeout(function () {
                    gsap.to(loader, {
                        opacity: 0,
                        duration: 0.6,
                        ease: 'power2.inOut',
                        onComplete: function () {
                            loader.style.display = 'none';
                            animateHero();
                        }
                    });
                }, 300);
            }
            progress.style.width = pct + '%';
        }, 120);
    }

    // ---- Hero Animation ----
    function animateHero() {
        var tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

        tl.to('.hero-tag', { opacity: 1, duration: 0.8 })
          .to('.hero-title .word', {
              opacity: 1,
              y: 0,
              duration: 1,
              stagger: 0.1,
          }, '-=0.4')
          .to('.hero-subtitle', { opacity: 1, duration: 0.8 }, '-=0.5')
          .to('.hero-cta', { opacity: 1, duration: 0.8 }, '-=0.5')
          .to('.scroll-indicator', { opacity: 1, duration: 0.8 }, '-=0.3');
    }

    // ---- Scroll Animations ----
    function initScrollAnimations() {
        gsap.registerPlugin(ScrollTrigger);

        ScrollTrigger.create({
            start: 'top -80',
            onUpdate: function (self) {
                document.getElementById('navbar').classList.toggle('scrolled', self.progress > 0);
            }
        });

        gsap.utils.toArray('.reveal-text').forEach(function (el) {
            gsap.to(el, {
                opacity: 1,
                y: 0,
                duration: 1,
                ease: 'power3.out',
                scrollTrigger: {
                    trigger: el,
                    start: 'top 85%',
                    toggleActions: 'play none none none',
                }
            });
        });

        gsap.utils.toArray('.reveal-up').forEach(function (el, i) {
            gsap.to(el, {
                opacity: 1,
                y: 0,
                duration: 0.8,
                delay: (i % 3) * 0.1,
                ease: 'power3.out',
                scrollTrigger: {
                    trigger: el,
                    start: 'top 88%',
                    toggleActions: 'play none none none',
                }
            });
        });

        gsap.utils.toArray('.stat-number').forEach(function (el) {
            var target = parseInt(el.getAttribute('data-count'));
            ScrollTrigger.create({
                trigger: el,
                start: 'top 90%',
                once: true,
                onEnter: function () {
                    gsap.to({ val: 0 }, {
                        val: target,
                        duration: 2,
                        ease: 'power2.out',
                        onUpdate: function () {
                            el.textContent = Math.floor(this.targets()[0].val);
                        }
                    });
                }
            });
        });
    }

    // ---- 3D Tilt Effect on Cards ----
    function initTiltCards() {
        var cards = document.querySelectorAll('[data-tilt]');
        cards.forEach(function (card) {
            card.addEventListener('mousemove', function (e) {
                var rect = card.getBoundingClientRect();
                var x = e.clientX - rect.left;
                var y = e.clientY - rect.top;
                var centerX = rect.width / 2;
                var centerY = rect.height / 2;
                var rotateX = (y - centerY) / centerY * -6;
                var rotateY = (x - centerX) / centerX * 6;
                card.style.transform = 'perspective(1000px) rotateX(' + rotateX + 'deg) rotateY(' + rotateY + 'deg) translateY(-4px)';
            });
            card.addEventListener('mouseleave', function () {
                card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) translateY(0)';
            });
        });
    }

    // ---- Mobile Menu ----
    function initMobileMenu() {
        var toggle = document.querySelector('.nav-toggle');
        var menu = document.getElementById('mobile-menu');
        var links = menu.querySelectorAll('.mobile-link');

        toggle.addEventListener('click', function () {
            toggle.classList.toggle('active');
            menu.classList.toggle('open');
            document.body.style.overflow = menu.classList.contains('open') ? 'hidden' : '';
        });

        links.forEach(function (link) {
            link.addEventListener('click', function () {
                toggle.classList.remove('active');
                menu.classList.remove('open');
                document.body.style.overflow = '';
            });
        });
    }

    // ---- Smooth Scroll ----
    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
            anchor.addEventListener('click', function (e) {
                var targetId = this.getAttribute('href');
                if (targetId === '#') return;
                e.preventDefault();
                var target = document.querySelector(targetId);
                if (target) {
                    var offset = 80;
                    var top = target.getBoundingClientRect().top + window.pageYOffset - offset;
                    window.scrollTo({ top: top, behavior: 'smooth' });
                }
            });
        });
    }

    // ---- Resize Handler ----
    function onResize() {
        windowW = window.innerWidth;
        windowH = window.innerHeight;
        if (camera && renderer) {
            camera.aspect = windowW / windowH;
            camera.updateProjectionMatrix();
            renderer.setSize(windowW, windowH);
        }
    }

    // ---- Init ----
    function init() {
        initLanguage();
        initThree();
        animateThree();
        initCursor();
        initLoader();
        initScrollAnimations();
        initTiltCards();
        initMobileMenu();
        initSmoothScroll();
        window.addEventListener('resize', onResize);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
