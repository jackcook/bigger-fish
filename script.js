const worker = new Worker("worker.js");

const collectTraceButton = document.getElementById("collect-trace");
const downloadTracesButton = document.getElementById("download-traces");

let recording = false;
let traces = [];
let lastTraceDone = true;

function getSelectedDuration() {
  let elm = document.getElementsByName("duration");

  for (i = 0; i < elm.length; i++) {
    if (elm[i].checked) return parseInt(elm[i].value);
  }

  return 5000;
}

function getSelectedSite() {
  let site = "none";
  elm = document.getElementsByName("site");

  for (i = 0; i < elm.length; i++) {
    if (elm[i].checked) site = elm[i].value;
  }

  if (site === "custom") {
    site = document.getElementById("custom-site-input").value;
  }

  return site === "none" ? null : site;
}

worker.onmessage = (e) => {
  const { trace, done, maxIndex } = JSON.parse(e.data);

  if (done) {
    recording = false;
  }

  // Trace dimensions
  const parent = document.getElementById("traces");
  const width = parent.getBoundingClientRect().width;
  const height = 64;

  if (lastTraceDone) {
    traces.push(trace);

    // Create new trace div
    const div = document.createElement("div");
    div.setAttribute("id", `t${traces.length}`);
    div.className = "trace";
    parent.appendChild(div);

    // Add label
    const duration = getSelectedDuration();
    const site = getSelectedSite();
    const mobile = window.matchMedia(
      "only screen and (max-width: 600px)"
    ).matches;
    const label = document.createElement("p");

    if (mobile) {
      label.innerText = `#${traces.length}: ${duration / 1000} second${
        duration === 1000 ? "" : "s"
      }`;
    } else {
      label.innerText = `#${traces.length}: ${
        site === null ? "None" : site.replace(/^https?:\/\//, "")
      }, ${duration / 1000} second${duration === 1000 ? "" : "s"}`;
    }
    div.appendChild(label);
  } else {
    traces[traces.length - 1] = trace;
  }

  lastTraceDone = done;

  const maxVal = d3.max(trace);
  const x = d3.scaleLinear().domain([0, trace.length]).range([0, width]);

  const color = d3
    .scaleQuantize()
    .range(["#0d0887", "#7e03a8", "#cc4778", "#f89540", "#f0f921"])
    .domain([0, maxVal]);

  // Remove the trace’s previously rendered content
  d3.select(`#t${traces.length}`).select("svg").remove();

  // Render the latest version of the trace
  const svg = d3
    .select(`#t${traces.length}`)
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .selectAll()
    .data(trace.map((x, i) => ({ index: i, value: x })))
    .join("rect")
    .attr("x", (d) => x(d.index))
    .attr("y", 0)
    .attr("width", x(1))
    .attr("height", height)
    .style("fill", (d) => (d.index > maxIndex ? "gray" : color(d.value)));

  if (done) {
    // Reset UI
    collectTraceButton.innerText = "Collect trace";
    collectTraceButton.className = "";
  }
};

collectTraceButton.onclick = () => {
  if (recording) return;

  // Update UI
  collectTraceButton.innerText = "Collecting trace...";
  collectTraceButton.className = "disabled";
  recording = true;

  // Get site
  const traceLength = getSelectedDuration();
  const site = getSelectedSite();

  if (site !== null) {
    const win = open(site, "_blank", "toolbar=1,location=1,menubar=1");

    // Close window after trace length
    setTimeout(() => win.close(), traceLength);
  }

  // Start collecting trace
  worker.postMessage({
    type: "start",
    traceLength,
  });
};

downloadTracesButton.onclick = () => {
  const blob = new Blob([JSON.stringify({ traces })], {
    type: "application/json",
  });

  const url = URL.createObjectURL(blob);

  const elem = document.createElement("a");
  elem.href = url;
  elem.download = "traces.json";
  document.body.appendChild(elem);

  elem.click();
  document.body.removeChild(elem);
};
