document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. CONFIGURATION ---
    const config = {
        nodeWidth: 200,
        nodeHeight: 60,
        colors: {
            locked: '#18181b',       
            lockedStroke: '#27272a', 
            active: '#1e1b4b',       
            activeStroke: '#6366f1', 
            mastered: '#064e3b',     
            masteredStroke: '#10b981' 
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
        .style("cursor", "grab");

    const defs = svg.append("defs");
    
    // Filters & Gradients
    const glow = defs.append("filter").attr("id", "blue-glow");
    glow.append("feGaussianBlur").attr("stdDeviation", "4").attr("result", "coloredBlur");
    const feMerge = glow.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    const linkGrad = defs.append("linearGradient").attr("id", "link-gradient").attr("gradientUnits", "userSpaceOnUse");
    linkGrad.append("stop").attr("offset", "0%").attr("stop-color", "#6366f1");
    linkGrad.append("stop").attr("offset", "100%").attr("stop-color", "#34d399");

    const lockPath = "M12 17a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm6-9h-1V6a5 5 0 0 0-10 0v2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2zM9 6a3 3 0 1 1 6 0v2H9V6z";

    // --- CSS INJECTION ---
    const style = document.createElement('style');
    style.innerHTML = `
        @keyframes flow { from { stroke-dashoffset: 24; } to { stroke-dashoffset: 0; } }
        .link { fill: none; stroke-linecap: round; transition: all 0.4s; }
        .link-inactive { stroke: #3f3f46; stroke-width: 1.5px; opacity: 0.3; }
        .link-active { 
            stroke: url(#link-gradient); 
            stroke-width: 2.5px; 
            stroke-dasharray: 8, 4; 
            animation: flow 1s linear infinite; 
            opacity: 0.8; 
            filter: drop-shadow(0 0 4px rgba(99, 102, 241, 0.4));
        }
        .node-group { transition: opacity 0.3s; }
        .dimmed { opacity: 0.15; filter: grayscale(100%); }
    `;
    document.head.appendChild(style);

    const g = svg.append("g");
    const tooltip = document.querySelector(".modern-tooltip");

    // --- 4. DRAWING ---
    const linkGen = d3.linkVertical().x(d => d[0]).y(d => d[1]);

    function generatePath(d) {
        return linkGen({
            source: [d.source.x, d.source.y + config.nodeHeight/2],
            target: [d.target.x, d.target.y - config.nodeHeight/2]
        });
    }

    const link = g.append("g").selectAll("path")
        .data(links).join("path")
        .attr("d", generatePath)
        .attr("class", "link link-inactive");

    const node = g.append("g").selectAll("g")
        .data(nodes).join("g")
        .attr("class", "node-group")
        .attr("transform", d => `translate(${d.x},${d.y})`)
        .style("cursor", "pointer")
        .on("click", (e, d) => {
            if (isUnlocked(d.id)) window.location.href = `/topic/${slugMap[d.id]}`;
        });

    // Node Background
    node.append("rect")
        .attr("x", -config.nodeWidth/2)
        .attr("y", -config.nodeHeight/2)
        .attr("width", config.nodeWidth)
        .attr("height", config.nodeHeight)
        .attr("rx", 10)
        .attr("class", "node-card")
        .attr("stroke-width", 1.5)
        .attr("fill", config.colors.locked)
        .attr("stroke", config.colors.lockedStroke);

    // Progress Bar (Background Fill)
    node.append("rect")
        .attr("x", -config.nodeWidth/2)
        .attr("y", -config.nodeHeight/2)
        .attr("height", config.nodeHeight)
        .attr("width", 0) // dynamic
        .attr("rx", 10)
        .attr("class", "node-progress")
        .attr("opacity", 0.15)
        .attr("fill", "#fff")
        .attr("clip-path", `inset(0 0 0 0 round 10px)`);

    // Lock Icon
    node.append("path")
        .attr("d", lockPath)
        .attr("transform", `translate(${-config.nodeWidth/2 + 20}, -12) scale(1)`)
        .attr("fill", "#52525b")
        .attr("class", "node-icon");

    // Text
    node.append("text")
        .attr("x", 0)
        .attr("y", 5)
        .attr("text-anchor", "middle")
        .attr("font-family", "Inter")
        .attr("font-size", "14px")
        .attr("font-weight", "600")
        .attr("fill", "#71717a")
        .attr("class", "node-label")
        .text(d => d.name);

    // --- 5. LOGIC & STATE ---
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
        return { pct: (count / allIds.length) * 100, str: `${count}/${allIds.length}` };
    }

    function isUnlocked(nodeId) {
        if(nodeId === 'AH') return true;
        const parents = prerequisites.get(nodeId) || [];
        return parents.every(pid => calculateProgress(pid).pct >= 50);
    }

    function updateState() {
        node.each(function(d) {
            const unlocked = isUnlocked(d.id);
            const prog = calculateProgress(d.id);
            const displayPct = unlocked ? prog.pct : 0;
            const mastered = displayPct === 100;

            const el = d3.select(this);
            const t = d3.transition().duration(600);

            // Determine Colors
            let stroke = config.colors.lockedStroke;
            let fill = config.colors.locked;
            let glowFilter = null;
            let labelColor = "#71717a";

            if (unlocked) {
                fill = config.colors.active;
                stroke = config.colors.activeStroke;
                labelColor = "#e4e4e7";
                glowFilter = "url(#blue-glow)";
                if (mastered) {
                    fill = config.colors.mastered;
                    stroke = config.colors.masteredStroke;
                }
            }

            el.select(".node-card").transition(t)
                .attr("stroke", stroke)
                .attr("fill", fill)
                .style("filter", glowFilter);

            el.select(".node-progress").transition(t)
                .attr("width", config.nodeWidth * (displayPct / 100))
                .attr("fill", mastered ? "#34d399" : "#818cf8");

            el.select(".node-icon").transition(t)
                .attr("opacity", unlocked ? 0 : 1);

            el.select(".node-label").transition(t)
                .attr("fill", labelColor);

            // Update Link Classes
            link.filter(l => l.source.id === d.id).attr("class", unlocked ? "link link-active" : "link link-inactive");
        });
    }

    // --- 6. INTERACTION (FOCUS MODE) ---
    
    function setFocus(d, isFocused) {
        if (!isFocused) {
            // Reset everything
            node.classed("dimmed", false);
            link.style("opacity", null);
            return;
        }

        // Identify related nodes (Parents + Children)
        const related = new Set();
        related.add(d.id);
        (prerequisites.get(d.id) || []).forEach(p => related.add(p));
        (outgoing.get(d.id) || []).forEach(c => related.add(c));

        // Dim unrelated nodes
        node.classed("dimmed", n => !related.has(n.id));

        // Highlight relevant links
        link.style("opacity", l => {
            if (l.source.id === d.id || l.target.id === d.id) return 1;
            return 0.05;
        });
    }

    node.on("mouseenter", function(e, d) {
        if(!isUnlocked(d.id)) return;

        // Visual Pop
        d3.select(this).transition().duration(200).attr("transform", `translate(${d.x},${d.y}) scale(1.05)`);
        
        // Focus Mode
        setFocus(d, true);

        // Tooltip
        const prog = calculateProgress(d.id);
        tooltip.innerHTML = `
            <div style="font-weight:700;margin-bottom:6px;font-size:14px;color:white;">${d.name}</div>
            <div style="display:flex;justify-content:space-between;font-size:12px;color:#9ca3af;">
                <span>Mastery</span>
                <span style="color:${prog.pct===100?'#34d399':'#818cf8'};font-family:'JetBrains Mono'">${Math.round(prog.pct)}%</span>
            </div>
            <div style="width:100%;height:4px;background:#333;margin-top:6px;border-radius:2px;overflow:hidden;">
                <div style="width:${prog.pct}%;height:100%;background:${prog.pct===100?'#34d399':'#6366f1'};"></div>
            </div>
        `;
        tooltip.classList.add("visible");
        tooltip.style.left = (e.clientX + 20) + "px"; 
        tooltip.style.top = (e.clientY - 40) + "px";

    }).on("mouseleave", function(e, d) {
        d3.select(this).transition().duration(200).attr("transform", `translate(${d.x},${d.y}) scale(1)`);
        setFocus(d, false);
        tooltip.classList.remove("visible");
    }).on("mousemove", e => { 
        tooltip.style.left = (e.clientX + 20) + "px"; 
        tooltip.style.top = (e.clientY - 40) + "px"; 
    });

    const zoom = d3.zoom().scaleExtent([0.3, 2]).on("zoom", e => g.attr("transform", e.transform));
    svg.call(zoom);
    const initialTransform = d3.zoomIdentity.translate(width/2, height/2 + 300).scale(0.65);
    svg.call(zoom.transform, initialTransform);
    
    document.getElementById("reset-button").onclick = () => {
        svg.transition().duration(800).call(zoom.transform, initialTransform);
    };

    fetchProgress();
    window.addEventListener('pageshow', () => fetchProgress());
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') fetchProgress(); });
});