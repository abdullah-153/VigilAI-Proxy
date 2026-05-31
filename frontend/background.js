/**
 * VigilAI Proxy Dashboard Background Mesh (background.js)
 * Ported mathematical grid canvas layout - Light Mode variant
 */

export function initSynapticCanvas() {
    const canvas = document.getElementById("bg-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    
    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;
    
    let mouse = { x: -1000, y: -1000, active: false };
    let points = [];
    let time = 0;
    
    const spacing = 55; // Grid cell spacing
    const gravityDist = 200; // Radius of mouse gravity well
    
    window.addEventListener("mousemove", (e) => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
        mouse.active = true;
    });
    
    window.addEventListener("mouseleave", () => {
        mouse.active = false;
        mouse.x = -1000;
        mouse.y = -1000;
    });

    window.addEventListener("touchstart", (e) => {
        if (e.touches && e.touches.length > 0) {
            mouse.x = e.touches[0].clientX;
            mouse.y = e.touches[0].clientY;
            mouse.active = true;
        }
    }, { passive: true });

    window.addEventListener("touchmove", (e) => {
        if (e.touches && e.touches.length > 0) {
            mouse.x = e.touches[0].clientX;
            mouse.y = e.touches[0].clientY;
            mouse.active = true;
        }
    }, { passive: true });

    window.addEventListener("touchend", () => {
        mouse.active = false;
        mouse.x = -1000;
        mouse.y = -1000;
    });
    
    window.addEventListener("resize", () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
        initGrid();
    });

    class GridPoint {
        constructor(col, row, baseX, baseY) {
            this.col = col;
            this.row = row;
            this.baseX = baseX;
            this.baseY = baseY;
            this.x = baseX;
            this.y = baseY;
            this.phase = Math.random() * Math.PI * 2;
            this.speed = 0.015 + Math.random() * 0.01;
            this.glow = 0;
        }

        update() {
            const wobbleX = Math.sin(time * this.speed + this.phase) * 1.5;
            const wobbleY = Math.cos(time * this.speed * 0.8 + this.phase) * 1.5;

            const scrollY = window.scrollY || 0;
            const scrollWobble = Math.sin(scrollY * 0.0035 + this.phase) * 1.2;

            let targetX = this.baseX + wobbleX;
            let targetY = this.baseY + wobbleY + scrollWobble;

            if (mouse.active) {
                const dx = mouse.x - this.baseX;
                const dy = mouse.y - this.baseY;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < gravityDist) {
                    const force = (gravityDist - dist) / gravityDist;
                    targetX -= (dx / (dist || 1)) * force * 12;
                    targetY -= (dy / (dist || 1)) * force * 12;
                    this.glow = force;
                } else {
                    this.glow += (0 - this.glow) * 0.08;
                }
            } else {
                this.glow += (0 - this.glow) * 0.08;
            }

            this.x += (targetX - this.x) * 0.12;
            this.y += (targetY - this.y) * 0.12;
        }
    }

    let cols = 0;
    let rows = 0;

    function initGrid() {
        points = [];
        cols = Math.ceil(width / spacing) + 4;
        rows = Math.ceil(height / spacing) + 4;
        
        for (let c = 0; c < cols; c++) {
            points[c] = [];
            for (let r = 0; r < rows; r++) {
                const baseX = (c - 2) * spacing;
                const baseY = (r - 2) * spacing;
                points[c][r] = new GridPoint(c, r, baseX, baseY);
            }
        }
    }

    initGrid();

    function animate() {
        ctx.clearRect(0, 0, width, height);
        time++;

        for (let c = 0; c < cols; c++) {
            for (let r = 0; r < rows; r++) {
                points[c][r].update();
            }
        }

        // Draw soft cyan mouse gravity radial glow
        if (mouse.active) {
            const radialGlow = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, 160);
            radialGlow.addColorStop(0, "rgba(6, 182, 212, 0.08)");
            radialGlow.addColorStop(1, "rgba(6, 182, 212, 0)");
            ctx.fillStyle = radialGlow;
            ctx.beginPath();
            ctx.arc(mouse.x, mouse.y, 160, 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.lineWidth = 0.55;
        for (let c = 0; c < cols; c++) {
            for (let r = 0; r < rows; r++) {
                const pt = points[c][r];
                
                // Draw horizontal line segments
                if (c < cols - 1) {
                    const ptRight = points[c+1][r];
                    const distMouse = mouse.active ? Math.min(
                        Math.sqrt((mouse.x - pt.x)**2 + (mouse.y - pt.y)**2),
                        Math.sqrt((mouse.x - ptRight.x)**2 + (mouse.y - ptRight.y)**2)
                    ) : 9999;

                    let alpha = 0.045;
                    let isGlowing = false;
                    let glowFactor = 0;
                    if (distMouse < gravityDist) {
                        glowFactor = (gravityDist - distMouse) / gravityDist;
                        alpha += glowFactor * 0.08;
                        isGlowing = true;
                    }
                    
                    if (isGlowing) {
                        ctx.save();
                        ctx.shadowBlur = glowFactor * 4;
                        ctx.shadowColor = `rgba(37, 99, 235, ${glowFactor * 0.15})`;
                        ctx.strokeStyle = `rgba(37, 99, 235, ${alpha})`;
                        ctx.beginPath();
                        ctx.moveTo(pt.x, pt.y);
                        ctx.lineTo(ptRight.x, ptRight.y);
                        ctx.stroke();
                        ctx.restore();
                    } else {
                        ctx.strokeStyle = `rgba(37, 99, 235, ${alpha})`;
                        ctx.beginPath();
                        ctx.moveTo(pt.x, pt.y);
                        ctx.lineTo(ptRight.x, ptRight.y);
                        ctx.stroke();
                    }
                }

                // Draw vertical line segments
                if (r < rows - 1) {
                    const ptDown = points[c][r+1];
                    const distMouse = mouse.active ? Math.min(
                        Math.sqrt((mouse.x - pt.x)**2 + (mouse.y - pt.y)**2),
                        Math.sqrt((mouse.x - ptDown.x)**2 + (mouse.y - ptDown.y)**2)
                    ) : 9999;

                    let alpha = 0.045;
                    let isGlowing = false;
                    let glowFactor = 0;
                    if (distMouse < gravityDist) {
                        glowFactor = (gravityDist - distMouse) / gravityDist;
                        alpha += glowFactor * 0.08;
                        isGlowing = true;
                    }

                    if (isGlowing) {
                        ctx.save();
                        ctx.shadowBlur = glowFactor * 4;
                        ctx.shadowColor = `rgba(37, 99, 235, ${glowFactor * 0.15})`;
                        ctx.strokeStyle = `rgba(37, 99, 235, ${alpha})`;
                        ctx.beginPath();
                        ctx.moveTo(pt.x, pt.y);
                        ctx.lineTo(ptDown.x, ptDown.y);
                        ctx.stroke();
                        ctx.restore();
                    } else {
                        ctx.strokeStyle = `rgba(37, 99, 235, ${alpha})`;
                        ctx.beginPath();
                        ctx.moveTo(pt.x, pt.y);
                        ctx.lineTo(ptDown.x, ptDown.y);
                        ctx.stroke();
                    }
                }

                // Draw grid nodes
                ctx.beginPath();
                ctx.arc(pt.x, pt.y, 0.75 + pt.glow * 0.8, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(37, 99, 235, ${0.05 + pt.glow * 0.15})`;
                ctx.fill();
            }
        }

        // Draw interactive crosshair indicators
        if (mouse.active) {
            ctx.save();
            ctx.strokeStyle = "rgba(6, 182, 212, 0.04)";
            ctx.lineWidth = 0.5;
            ctx.setLineDash([4, 6]);

            ctx.beginPath();
            ctx.moveTo(mouse.x, 0);
            ctx.lineTo(mouse.x, height);
            ctx.stroke();

            ctx.beginPath();
            ctx.moveTo(0, mouse.y);
            ctx.lineTo(width, mouse.y);
            ctx.stroke();
            ctx.restore();
        }

        requestAnimationFrame(animate);
    }

    animate();
}
