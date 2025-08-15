document.addEventListener('DOMContentLoaded', () => {

    // --- PARTICLE ANIMATION SETUP ---
    tsParticles.load("particles-bg", {
        fpsLimit: 120,
        background: { color: "#1e1b34" },
        interactivity: {
            events: {
                onHover: { enable: true, mode: ["repulse", "bubble"] },
            },
            modes: {
                repulse: { distance: 100, duration: 0.4 },
                bubble: { distance: 200, size: 2.5, opacity: 0.8 },
            },
        },
        particles: {
            color: { value: ["#ffffff", "#a78bfa", "#2dd4bf"] },
            links: {
                color: "rgba(167, 139, 250, 0.2)",
                distance: 150,
                enable: true,
                opacity: 0.2,
                width: 1,
            },
            move: {
                direction: "bottom-right",
                enable: true,
                outModes: "out",
                random: true,
                speed: 0.3,
                straight: false,
            },
            number: { density: { enable: true, area: 1200 }, value: 50 },
            opacity: { value: { min: 0.1, max: 0.4 } },
            shape: { type: "circle" },
            size: { value: { min: 0.5, max: 2 } },
        },
        detectRetina: true,
    });

    // --- 1. DATA AND LAYOUT DEFINITION ---
    const slugMap = {
        "AH": "arrays-hashing", "TP": "two-pointers", "S": "stack", "BS": "binary-search", 
        "SW": "sliding-window", "LL": "linked-list", "T": "trees", "Tr": "tries", 
        "HPQ": "heap-priority-queue", "BT": "backtracking", "I": "intervals", "G": "greedy",
        "AG": "advanced-graphs", "Gr": "graphs", "DP1": "1-d-dp", "DP2": "2-d-dp", 
        "BM": "bit-manipulation", "MG": "math-geometry"
    };

    const nodes = [
        { id: "AH", name: "Arrays & Hashing",    x: 0,    y: -900 },
        { id: "TP", name: "Two Pointers",        x: -500, y: -700 },
        { id: "S",  name: "Stack",               x: 500,  y: -700 },
        { id: "BS", name: "Binary Search",       x: -750, y: -500 },
        { id: "SW", name: "Sliding Window",      x: -250, y: -500 },
        { id: "LL", name: "Linked List",         x: 500,  y: -500 },
        { id: "T",  name: "Trees",               x: -250, y: -300 },
        { id: "Tr", name: "Tries",               x: -800, y: -50 },
        { id: "HPQ",name: "Heap / Priority Queue", x: -250, y: -50 },
        { id: "BT", name: "Backtracking",        x: 550,  y: -50 },
        { id: "I",  name: "Intervals",           x: -850, y: 200 },
        { id: "G",  name: "Greedy",              x: -500, y: 200 },
        { id: "AG", name: "Advanced Graphs",     x: -100, y: 200 },
        { id: "Gr", name: "Graphs",              x: 350,  y: 200 },
        { id: "DP1",name: "1-D DP",              x: 750,  y: 200 },
        { id: "DP2",name: "2-D DP",              x: 300,  y: 450 },
        { id: "BM", name: "Bit Manipulation",    x: 750,  y: 450 },
        { id: "MG", name: "Math & Geometry",     x: 500,  y: 650 }
    ];
    
    const linksData = [
        { source: "AH", target: "TP" }, { source: "AH", target: "S" },
        { source: "TP", target: "BS" }, { source: "TP", target: "SW" }, { source: "TP", target: "LL" },
        { source: "BS", target: "T" }, { source: "SW", target: "T" }, { source: "LL", target: "T" },
        { source: "T", target: "Tr" }, { source: "T", target: "HPQ" }, { source: "T", target: "BT" },
        { source: "HPQ", target: "I" }, { source: "HPQ", target: "G" }, { source: "HPQ", target: "AG" },
        { source: "BT", target: "Gr" }, { source: "BT", target: "DP1" },
        { source: "Gr", target: "AG" }, { source: "Gr", target: "DP2" },
        { source: "DP1", target: "DP2" }, { source: "DP1", target: "BM" },
        { source: "DP2", target: "MG" }, { source: "BM", target: "MG" }
    ];

    const nodeMap = new Map(nodes.map(node => [node.id, node]));
    const links = linksData.map(link => ({ source: nodeMap.get(link.source), target: nodeMap.get(link.target) }));
    
    const prerequisites = new Map();
    nodes.forEach(n => prerequisites.set(n.id, []));
    linksData.forEach(l => prerequisites.get(l.target).push(l.source));

    // --- 2. SVG SETUP & NEW GRADIENTS ---
    const container = document.getElementById('graph-container');
    const width = container.clientWidth;
    const height = container.clientHeight;
    const svg = d3.select("#graph-container").append("svg").attr("width", width).attr("height", height);
    const defs = svg.append("defs");
    
    const nodeBgGradient = defs.append("linearGradient")
        .attr("id", "node-bg-gradient")
        .attr("x1", "0%").attr("y1", "0%")
        .attr("x2", "100%").attr("y2", "100%");
    nodeBgGradient.append("stop").attr("offset", "0%").style("stop-color", "#2f2b54");
    nodeBgGradient.append("stop").attr("offset", "100%").style("stop-color", "#232044");

    const glowFilter = defs.append("filter").attr("id", "node-glow").attr("x", "-50%").attr("y", "-50%").attr("width", "200%").attr("height", "200%");
    glowFilter.append("feGaussianBlur").attr("stdDeviation", "8").attr("result", "coloredBlur");
    const feMerge = glowFilter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    const progressGradient = defs.append("linearGradient").attr("id", "progress-gradient");
    progressGradient.append("stop").attr("offset", "0%").style("stop-color", "#2dd4bf");
    progressGradient.append("stop").attr("offset", "100%").style("stop-color", "#a78bfa");

    // --- CHANGE: Updated arrowhead style for better visibility ---
    defs.append("marker").attr("id", "arrowhead").attr("viewBox", "0 -5 10 10").attr("refX", 12).attr("refY", 0).attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto").append("path").attr("d", "M0,-5L10,0L0,5Z").attr("fill", "#8b83b3");
    defs.append("marker").attr("id", "arrowhead-hover").attr("viewBox", "0 -5 10 10").attr("refX", 12).attr("refY", 0).attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto").append("path").attr("d", "M0,-5L10,0L0,5Z").attr("fill", "#f9fafb");
    
    const g = svg.append("g");
    const tooltip = d3.select(".graph-tooltip");
    
    // --- 3. RENDERING ELEMENTS ---
    const nodeHeight = 84;
    const nodeWidth = d => d.name.length * 14 + 130; 
    const barHeight = 11;
    const barYOffset = 26;
    const barPadding = 28;
    
    function generatePath(d) {
        const sourceY = d.source.y + (nodeHeight / 2) - 4;
        const targetY = d.target.y - (nodeHeight / 2) - 4;
        return d3.linkVertical()({ source: [d.source.x, sourceY], target: [d.target.x, targetY] });
    }

    // --- CHANGE: Updated link style for better visibility ---
    const link = g.append("g").attr("stroke", "#8b83b3").attr("stroke-width", 2.5).attr("fill", "none").selectAll("path").data(links).join("path").attr("d", generatePath).attr("marker-end", "url(#arrowhead)");
    
    const node = g.append("g").selectAll("g").data(nodes).join("g")
        .attr("transform", d => `translate(${d.x},${d.y})`)
        .on("click", (event, d) => {
            if (!isUnlocked(d.id)) {
                tooltip.html(`Complete 50% of<br>prerequisite topics to unlock!`).style("opacity", 1);
                return;
            };
            window.location.href = `/topic/${slugMap[d.id]}`;
        });
        
    node.append("rect")
        .attr("class", "node-background")
        .attr("width", nodeWidth).attr("height", nodeHeight).attr("rx", 32).attr("ry", 32)
        .style("fill", "url(#node-bg-gradient)")
        .attr("stroke", "#a78bfa")
        .attr("stroke-width", 2.5).style("filter", "url(#node-glow)")
        .attr("x", d => -nodeWidth(d) / 2).attr("y", -nodeHeight / 2);
    node.append("rect")
        .attr("class", "progress-bar-bg")
        .attr("width", d => nodeWidth(d) - barPadding * 2).attr("height", barHeight).attr("rx", barHeight / 2).attr("ry", barHeight / 2)
        .style("fill", "rgba(0,0,0,0.4)").attr("x", d => -(nodeWidth(d) - barPadding * 2) / 2).attr("y", barYOffset);
    node.append("rect")
        .attr("class", "progress-bar-fill")
        .attr("width", 0).attr("height", barHeight).attr("rx", barHeight / 2).attr("ry", barHeight / 2)
        .style("fill", "url(#progress-gradient)").style("filter", "drop-shadow(0 0 5px rgba(45, 212, 191, 0.5))")
        .attr("x", d => -(nodeWidth(d) - barPadding * 2) / 2).attr("y", barYOffset);
    
    node.append("text")
        .attr("fill", "#e5e7eb").attr("font-weight", "500")
        .attr("font-size", "24px")
        .attr("text-anchor", "middle").attr("y", -6)
        .text(d => d.name).style("pointer-events", "none");
    
    // --- 4. PROGRESS & UNLOCKING LOGIC ---
    function getSolvedMap() {
        return new Map(Object.entries(JSON.parse(localStorage.getItem('solvedProblems') || '{}')));
    }

    function calculateProgress(nodeId) {
        const solvedMap = getSolvedMap();
        const solvedIds = new Set(Array.from(solvedMap.keys()).map(Number));
        const slug = slugMap[nodeId];
        if (!topicProblemsMap[slug]) return { solved: 0, total: 0, percentage: 0 };
        const allProblemIds = topicProblemsMap[slug];
        if (allProblemIds.length === 0) return { solved: 0, total: 0, percentage: 0 };
        const solvedCount = allProblemIds.filter(id => solvedIds.has(id)).length;
        return {
            solved: solvedCount,
            total: allProblemIds.length,
            percentage: allProblemIds.length > 0 ? (solvedCount / allProblemIds.length) * 100 : 0
        };
    }

    function isUnlocked(nodeId) {
        if (nodeId === 'AH') return true;
        const parentIds = prerequisites.get(nodeId) || [];
        if (parentIds.length === 0) return true;
        
        return parentIds.every(parentId => {
            const progress = calculateProgress(parentId);
            return progress.percentage >= 50;
        });
    }

    function updateNodeStates() {
        node.each(function(d) {
            const unlocked = isUnlocked(d.id);
            const sel = d3.select(this);
            sel.classed('locked', !unlocked)
               .style('cursor', unlocked ? 'pointer' : 'not-allowed');
            
            sel.select(".node-background").transition().duration(750)
                .style("fill", unlocked ? "url(#node-bg-gradient)" : "#374151")
                .attr("stroke", unlocked ? "#a78bfa" : "#4b5563");
            
            sel.transition().duration(750).attr('opacity', unlocked ? 1.0 : 0.6);

            link.filter(l => l.target.id === d.id)
                .transition().duration(750)
                .attr('stroke-dasharray', unlocked ? 'none' : '4, 4');
        });
    }

    function updateProgressBars() {
        node.each(function(d) {
            const progress = calculateProgress(d.id);
            const el = d3.select(this);
            const barContainerWidth = nodeWidth(d) - barPadding * 2;
            
            el.select(".progress-bar-fill")
              .transition().duration(750)
              .attr("width", barContainerWidth * (progress.percentage / 100));

            el.classed('completed', progress.percentage === 100);
        });
        updateNodeStates();
    }
    
    // --- 5. ZOOM/PAN & INTERACTIVITY SETUP ---
    const bounds = g.node().getBBox();
    const fullWidth = bounds.width;
    const fullHeight = bounds.height;
    const midX = bounds.x + fullWidth / 2;
    const midY = bounds.y + fullHeight / 2;
    
    const initialScale = 1.0 / Math.max(fullWidth / width, fullHeight / height);
    
    const initialTranslate = [width / 2 - initialScale * midX, height / 2 - initialScale * midY];
    const zoom = d3.zoom().scaleExtent([initialScale * 0.5, 3]).translateExtent([[bounds.x - 200, bounds.y - 200], [bounds.x + fullWidth + 200, bounds.y + fullHeight + 200]]).on("zoom", (event) => g.attr("transform", event.transform));
    const initialTransform = d3.zoomIdentity.translate(initialTranslate[0], initialTranslate[1]).scale(initialScale);
    svg.call(zoom).transition().duration(750).call(zoom.transform, initialTransform);
    
    node.on('mouseover', handleMouseOver)
        .on('mousemove', handleMouseMove)
        .on('mouseout', handleMouseOut);
    
    function handleMouseOver(event, d) {
        const unlocked = isUnlocked(d.id);
        if (!unlocked) return;

        const sel = d3.select(this);
        sel.transition().duration(200).attr("transform", `translate(${d.x},${d.y}) scale(1.05)`);
        const linkedIds = new Set([d.id, ...links.flatMap(l => l.source.id === d.id ? [l.target.id] : l.target.id === d.id ? [l.source.id] : [])]);
        node.transition().duration(200).attr('opacity', n => isUnlocked(n.id) ? (linkedIds.has(n.id) ? 1.0 : 0.4) : 0.6);
        // --- CHANGE: Updated hover color to use new base color ---
        link.transition().duration(200).attr('stroke', l => (l.source === d || l.target === d) ? '#f9fafb' : '#8b83b3').attr('stroke-opacity', l => (l.source === d || l.target === d) ? 1.0 : 0.3).attr('marker-end', l => (l.source === d || l.target === d) ? 'url(#arrowhead-hover)' : 'url(#arrowhead)');
        tooltip.style("opacity", 1);
    }
    
    function handleMouseMove(event, d) {
        const progress = calculateProgress(d.id);
        tooltip.html(`${d.name}<br>Progress: ${progress.solved} / ${progress.total} (${progress.percentage.toFixed(0)}%)`)
            .style("left", (event.pageX + 15) + "px")
            .style("top", "auto")
            .style("bottom", (window.innerHeight - event.pageY + 15) + "px");
    }

    function handleMouseOut(event, d) {
        const sel = d3.select(this);
        sel.transition().duration(200).attr("transform", `translate(${d.x},${d.y}) scale(1.0)`);
        updateNodeStates();
        // --- CHANGE: Updated mouseout color to new base color ---
        link.transition().duration(200).attr('stroke', '#8b83b3').attr('stroke-opacity', 1.0).attr('marker-end', 'url(#arrowhead)');
        tooltip.style("opacity", 0);
    }
    
    document.getElementById('reset-button').addEventListener('click', () => {
        svg.transition().duration(750).call(zoom.transform, initialTransform);
    });

    updateProgressBars(); 
    window.addEventListener('pageshow', (event) => {
        if (event.persisted) { 
            updateProgressBars();
        }
    });
});