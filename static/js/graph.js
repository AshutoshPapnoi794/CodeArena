document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. CONFIGURATION ---
    const config = {
        nodeWidth: 220,
        nodeHeight: 64,
        cornerSize: 10,
        colors: {
            locked: { stroke: '#27272a', fill: '#09090b', text: '#52525b' },
            unlocked: { stroke: '#6366f1', fill: '#1e1b4b', text: '#e4e4e7', glow: '#6366f1' },
            mastered: { stroke: '#10b981', fill: '#064e3b', text: '#ecfdf5', glow: '#10b981' }
        }
    };

    // --- 2. DATA ---
    const nodes = [
        { id: "AH", name: "Arrays & Hashing",    x: 0,    y: -500 },
        { id: "TP", name: "Two Pointers",        x: -250, y: -300 },
        { id: "S",  name: "Stack",               x: 250,  y: -300 },
        { id: "BS", name: "Binary Search",       x: -350, y: -100 },
        { id: "SW", name: "Sliding Window",      x: -150, y: -100 },
        { id: "LL", name: "Linked List",         x: 350,  y: -100 },
        { id: "T",  name: "Trees",               x: 0,    y: 100 },
        { id: "Tr", name: "Tries",               x: -300, y: 300 },
        { id: "HPQ",name: "Heap / PQ",           x: 0,    y: 300 },
        { id: "BT", name: "Backtracking",        x: 300,  y: 300 },
        { id: "Gr", name: "Graphs",              x: 0,    y: 500 },
        { id: "DP1",name: "1-D DP",              x: 400,  y: 500 },
        { id: "I",  name: "Intervals",           x: -400, y: 500 },
        { id: "AG", name: "Advanced Graphs",     x: -200, y: 700 },
        { id: "DP2",name: "2-D DP",              x: 200,  y: 700 },
        { id: "BM", name: "Bit Manipulation",    x: 450,  y: 800 },
        { id: "MG", name: "Math & Geometry",     x: 0,    y: 850 },
        { id: "G",  name: "Greedy",              x: -450, y: 800 }
    ];

    const slugMap = { "AH": "arrays-hashing", "TP": "two-pointers", "S": "stack", "BS": "binary-search", "SW": "sliding-window", "LL": "linked-list", "T": "trees", "Tr": "tries", "HPQ": "heap-priority-queue", "BT": "backtracking", "I": "intervals", "G": "greedy", "AG": "advanced-graphs", "Gr": "graphs", "DP1": "1-d-dp", "DP2": "2-d-dp", "BM": "bit-manipulation", "MG": "math-geometry" };
    
    const linksData = [ 
        { source: "AH", target: "TP" }, { source: "AH", target: "S" }, 
        { source: "TP", target: "BS" }, { source: "TP", target: "SW" }, { source: "TP", target: "LL" }, 
        { source: "BS", target: "T" }, { source: "SW", target: "T" }, { source: "LL", target: "T" }, 
        { source: "T", target: "Tr" }, { source: "T", target: "HPQ" }, { source: "T", target: "BT" }, 
        { source: "HPQ", target: "I" }, { source: "HPQ", target: "G" }, 
        { source: "BT", target: "Gr" }, { source: "BT", target: "DP1" }, 
        { source: "Gr", target: "AG" }, { source: "Gr", target: "DP2" }, 
        { source: "DP1", target: "DP2" }, { source: "DP1", target: "BM" }, 
        { source: "DP2", target: "MG" }
    ];

    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    const links = linksData.map(l => ({ source: nodeMap.get(l.source), target: nodeMap.get(l.target) }));
    
    const prerequisites = new Map();
    nodes.forEach(n => prerequisites.set(n.id, []));
    linksData.forEach(l => prerequisites.get(l.target).push(l.source));

    // Get outgoing links for focus mode
    const outgoing = new Map();
    nodes.forEach(n => outgoing.set(n.id, []));
    linksData.forEach(l => outgoing.get(l.source).push(l.target));

    // --- 3. D3 SETUP ---
    const container = document.getElementById('graph-container');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    const svg = d3.select("#graph-container").append("svg")
        .attr("width", width).attr("height", height)
        .style("cursor", "grab")
        .attr("viewBox", [0, 0, width, height]);

    // --- DEFS (Advanced Filters & Patterns) ---
    const defs = svg.append("defs");
    
    // 1. Grid Pattern for Background (Subtle Tech feel)
    const gridPattern = defs.append("pattern")
        .attr("id", "tech-grid")
        .attr("width", 50).attr("height", 50)
        .attr("patternUnits", "userSpaceOnUse");
    gridPattern.append("path")
        .attr("d", "M 50 0 L 0 0 0 50")
        .attr("fill", "none")
        .attr("stroke", "rgba(255,255,255,0.03)")
        .attr("stroke-width", 1);

    // 2. Diagonal Stripe for Locked Nodes
    const stripePattern = defs.append("pattern")
        .attr("id", "diagonal-stripe")
        .attr("width", 10).attr("height", 10)
        .attr("patternUnits", "userSpaceOnUse")
        .attr("patternTransform", "rotate(45)");
    stripePattern.append("rect").attr("width", 5).attr("height", 10).attr("fill", "#000");
    stripePattern.append("rect").attr("x", 5).attr("width", 5).attr("height", 10).attr("fill", "#333");

    // 3. Link Gradient (Animated feel via color)
    const linkGrad = defs.append("linearGradient")
        .attr("id", "link-gradient")
        .attr("gradientUnits", "userSpaceOnUse");
    linkGrad.append("stop").attr("offset", "0%").attr("stop-color", "#6366f1").attr("stop-opacity", 0.1);
    linkGrad.append("stop").attr("offset", "50%").attr("stop-color", "#818cf8");
    linkGrad.append("stop").attr("offset", "100%").attr("stop-color", "#34d399").attr("stop-opacity", 0.1);

    // 4. Glow Filter
    const filter = defs.append("filter").attr("id", "glow");
    filter.append("feGaussianBlur").attr("stdDeviation", "2.5").attr("result", "coloredBlur");
    const feMerge = filter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    // --- BACKGROUND GRID RENDER ---
    const bgGroup = svg.append("g").attr("class", "background-layer");
    bgGroup.append("rect")
        .attr("x", -5000).attr("y", -5000)
        .attr("width", 10000).attr("height", 10000)
        .attr("fill", "url(#tech-grid)");

    const mainGroup = svg.append("g");
    const tooltip = document.querySelector(".modern-tooltip");

    // --- 4. DRAWING UTILS ---
    const linkGen = d3.linkVertical().x(d => d[0]).y(d => d[1]);

    // Generate "Tech Card" Path with cutout corners
    function getCardPath(w, h, r) {
        // Top Left, Top Right, Bottom Right, Bottom Left
        return `
            M ${r},0 
            L ${w-r},0 L ${w},${r} 
            L ${w},${h-r} L ${w-r},${h} 
            L ${r},${h} L 0,${h-r} 
            L 0,${r} Z
        `;
    }

    // Generate "Corner Brackets" Path
    function getCornerPath(w, h, len) {
        return `
            M 0,${len} L 0,0 L ${len},0 
            M ${w-len},0 L ${w},0 L ${w},${len}
            M ${w},${h-len} L ${w},${h} L ${w-len},${h}
            M ${len},${h} L 0,${h} L 0,${h-len}
        `;
    }

    // --- 5. RENDER LINKS ---
    // Layer 1: Base dark lines
    mainGroup.append("g").selectAll("path")
        .data(links).join("path")
        .attr("class", "link-base")
        .attr("d", d => linkGen({
            source: [d.source.x, d.source.y + config.nodeHeight/2],
            target: [d.target.x, d.target.y - config.nodeHeight/2]
        }));

    // Layer 2: Active Gradient Path (Revealed via CSS/JS)
    const activeLinks = mainGroup.append("g").selectAll("path")
        .data(links).join("path")
        .attr("class", "link-active-path")
        .attr("id", d => `link-${d.source.id}-${d.target.id}`)
        .attr("d", d => linkGen({
            source: [d.source.x, d.source.y + config.nodeHeight/2],
            target: [d.target.x, d.target.y - config.nodeHeight/2]
        }))
        .attr("opacity", 0); // Hidden by default

    // Layer 3: Data Particles (The flow animation)
    const particles = mainGroup.append("g").selectAll("path")
        .data(links).join("path")
        .attr("class", "link-particle")
        .attr("id", d => `part-${d.source.id}-${d.target.id}`)
        .attr("d", d => linkGen({
            source: [d.source.x, d.source.y + config.nodeHeight/2],
            target: [d.target.x, d.target.y - config.nodeHeight/2]
        }))
        .attr("opacity", 0);

    // --- 6. RENDER NODES ---
    const nodeGroup = mainGroup.append("g").selectAll("g")
        .data(nodes).join("g")
        .attr("class", "node-container")
        .attr("transform", d => `translate(${d.x - config.nodeWidth/2},${d.y - config.nodeHeight/2})`)
        .on("click", (e, d) => {
            if (isUnlocked(d.id)) window.location.href = `/topic/${slugMap[d.id]}`;
        });

    // A. Glass Background
    nodeGroup.append("path")
        .attr("d", getCardPath(config.nodeWidth, config.nodeHeight, config.cornerSize))
        .attr("class", "node-glass");

    // B. Locked Texture Overlay
    nodeGroup.append("path")
        .attr("d", getCardPath(config.nodeWidth, config.nodeHeight, config.cornerSize))
        .attr("class", "locked-pattern node-locked-overlay");

    // C. Border
    nodeGroup.append("path")
        .attr("d", getCardPath(config.nodeWidth, config.nodeHeight, config.cornerSize))
        .attr("class", "node-border")
        .attr("stroke", config.colors.locked.stroke);

    // D. Corner Brackets (Tech decoration)
    nodeGroup.append("path")
        .attr("d", getCornerPath(config.nodeWidth, config.nodeHeight, 15))
        .attr("class", "node-corners")
        .attr("stroke", config.colors.locked.stroke)
        .attr("opacity", 0.5);

    // E. Text Label
    nodeGroup.append("text")
        .attr("x", 20)
        .attr("y", config.nodeHeight/2 - 2)
        .attr("class", "node-text")
        .attr("fill", config.colors.locked.text)
        .text(d => d.name);

    // F. Progress/Subtext Label
    nodeGroup.append("text")
        .attr("x", 20)
        .attr("y", config.nodeHeight/2 + 14)
        .attr("class", "node-subtext")
        .attr("fill", config.colors.locked.text)
        .text("LOCKED // ACCESS DENIED");

    // G. Status Icon (Right side)
    const iconGroup = nodeGroup.append("g")
        .attr("transform", `translate(${config.nodeWidth - 40}, ${config.nodeHeight/2 - 10})`);
    
    // Lock Icon
    iconGroup.append("path")
        .attr("class", "icon-lock")
        .attr("d", "M6 10V7a4 4 0 1 1 8 0v3h1a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h1zm2-3a2 2 0 1 1 4 0v3H8V7z")
        .attr("fill", "#52525b")
        .attr("transform", "scale(1.0)");

    // --- 7. LOGIC & ANIMATION LOOP ---
    let solvedMapCache = new Map();

    async function fetchProgress() {
        try {
            const res = await fetch(`/api/progress?t=${Date.now()}`);
            if(res.ok) {
                solvedMapCache = new Map(Object.entries(await res.json()));
                updateState();
            }
        } catch(e) {}
    }

    function calculateProgress(nodeId) {
        const slug = slugMap[nodeId];
        const allIds = (topicProblemsMap[slug] || []).map(String);
        if(!allIds.length) return { pct: 0, str: "0/0" };
        const count = allIds.filter(id => solvedMapCache.has(id)).length;
        return { pct: (count / allIds.length) * 100, str: `${count} / ${allIds.length}` };
    }

    function isUnlocked(nodeId) {
        if(nodeId === 'AH') return true;
        const parents = prerequisites.get(nodeId) || [];
        return parents.every(pid => calculateProgress(pid).pct >= 50);
    }

    function updateState() {
        nodeGroup.each(function(d) {
            const unlocked = isUnlocked(d.id);
            const prog = calculateProgress(d.id);
            const mastered = prog.pct === 100;
            
            const g = d3.select(this);
            const t = d3.transition().duration(600);
            
            // Colors
            let theme = config.colors.locked;
            if (unlocked) theme = config.colors.unlocked;
            if (mastered) theme = config.colors.mastered;

            // Update Border & Corners
            g.select(".node-border").transition(t)
                .attr("stroke", theme.stroke)
                .attr("filter", unlocked ? "url(#glow)" : null);
            
            g.select(".node-corners").transition(t)
                .attr("stroke", theme.stroke)
                .attr("opacity", unlocked ? 1 : 0.3);

            // Update Backgrounds
            g.select(".node-glass").transition(t)
                .attr("fill", unlocked ? "rgba(10, 10, 20, 0.4)" : "rgba(0,0,0,0.8)"); // Clearer glass when unlocked
            
            g.select(".node-locked-overlay").transition(t)
                .attr("opacity", unlocked ? 0 : 0.15);

            // Update Text
            g.select(".node-text").transition(t).attr("fill", theme.text);
            g.select(".node-subtext").transition(t)
                .attr("fill", theme.text)
                .textTween(function() {
                    const el = d3.select(this);
                    if (!unlocked) return () => "LOCKED // ACCESS DENIED";
                    if (mastered) return () => "STATUS: MASTERED // 100%";
                    return () => `PROGRESS: ${Math.round(prog.pct)}% // ${prog.str}`;
                });

            // Icons
            g.select(".icon-lock").transition(t).attr("opacity", unlocked ? 0 : 1);
            
            // Link Animations (Update visibility based on unlock status)
            activeLinks.filter(l => l.source.id === d.id)
                .transition(t)
                .attr("opacity", unlocked ? 1 : 0);
                
            particles.filter(l => l.source.id === d.id)
                .transition(t)
                .attr("opacity", unlocked ? 1 : 0);
        });
    }

    // --- 8. LINK FLOW ANIMATION ---
    // Instead of CSS stroke-dashoffset (which can be jerky with gradient),
    // we use a D3 timer to smoothly animate the "Particle" dash offset
    d3.timer((elapsed) => {
        particles.attr("stroke-dashoffset", -elapsed * 0.1);
    });


    // --- 9. INTERACTION: FOCUS MODE ---
    function setFocus(d, isFocused) {
        if (!isFocused) {
            nodeGroup.classed("dimmed", false).classed("highlighted", false);
            activeLinks.attr("opacity", l => isUnlocked(l.source.id) ? 1 : 0);
            particles.attr("opacity", l => isUnlocked(l.source.id) ? 1 : 0);
            return;
        }

        // Find related
        const related = new Set();
        related.add(d.id);
        (prerequisites.get(d.id) || []).forEach(p => related.add(p));
        (outgoing.get(d.id) || []).forEach(c => related.add(c));

        // Dim unrelated
        nodeGroup.classed("dimmed", n => !related.has(n.id));
        nodeGroup.classed("highlighted", n => n.id === d.id);

        // Dim unrelated links
        activeLinks.attr("opacity", l => {
            if (l.source.id === d.id || l.target.id === d.id) return 1;
            return 0.05;
        });
        particles.attr("opacity", l => {
            if (l.source.id === d.id || l.target.id === d.id) return 1;
            return 0;
        });
    }

    nodeGroup.on("mouseenter", function(e, d) {
        if(!isUnlocked(d.id)) return;
        
        // Pop effect
        d3.select(this).transition().duration(200)
            .attr("transform", `translate(${d.x - config.nodeWidth/2},${d.y - config.nodeHeight/2}) scale(1.05)`);

        setFocus(d, true);

        // HTML Tooltip
        const prog = calculateProgress(d.id);
        const color = prog.pct === 100 ? config.colors.mastered.glow : config.colors.unlocked.glow;
        
        tooltip.innerHTML = `
            <div style="padding: 12px 16px; border-left: 3px solid ${color}; background: rgba(0,0,0,0.8);">
                <div style="font-weight:700; font-size:14px; color:white; letter-spacing:0.5px; text-transform:uppercase;">${d.name}</div>
                <div style="margin-top:6px; display:flex; justify-content:space-between; font-size:11px; color:#a1a1aa; font-family:'JetBrains Mono'">
                    <span>MASTERY</span>
                    <span style="color:${color}">${Math.round(prog.pct)}%</span>
                </div>
                <!-- Mini Progress Bar -->
                <div style="width:100%; height:2px; background:#333; margin-top:4px; position:relative;">
                    <div style="position:absolute; left:0; top:0; height:100%; width:${prog.pct}%; background:${color}; box-shadow: 0 0 10px ${color};"></div>
                </div>
            </div>
        `;
        tooltip.classList.add("visible");
        updateTooltipPos(e);

    }).on("mouseleave", function(e, d) {
        d3.select(this).transition().duration(200)
            .attr("transform", `translate(${d.x - config.nodeWidth/2},${d.y - config.nodeHeight/2}) scale(1)`);
        setFocus(d, false);
        tooltip.classList.remove("visible");
    }).on("mousemove", updateTooltipPos);

    function updateTooltipPos(e) {
        tooltip.style.left = (e.clientX + 20) + "px"; 
        tooltip.style.top = (e.clientY - 40) + "px";
    }

    // --- 10. ZOOM & PAN ---
    const zoom = d3.zoom()
        .scaleExtent([0.4, 2])
        .on("zoom", e => {
            mainGroup.attr("transform", e.transform);
            // Parallax the background grid slightly
            bgGroup.attr("transform", `translate(${e.transform.x * 0.2}, ${e.transform.y * 0.2}) scale(${e.transform.k})`);
        });

    svg.call(zoom);
    
    // Initial Position
    const initialTransform = d3.zoomIdentity.translate(width/2, height/2 + 300).scale(0.75);
    svg.call(zoom.transform, initialTransform);
    
    document.getElementById("reset-button").onclick = () => {
        svg.transition().duration(1000).call(zoom.transform, initialTransform);
    };

    fetchProgress();
    window.addEventListener('pageshow', () => fetchProgress());
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') fetchProgress(); });
});