import { useEffect, useState } from "react";
import "./App.css";
import GraphDisplay from "./components/GraphDisplay";

function App() {
  const [graphList, setGraphList] = useState([]); // Stores list of graphs
  const [selectedGraphs, setSelectedGraphs] = useState([]); // Stores selected graphs
  const [graphHtml, setGraphHtml] = useState(""); // Stores HTML response from backend
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState<File | null>(null); // Stores uploaded file
  const [file_id, setFileID] = useState('');

  // // Fetch the list of available graphs from the backend
  // useEffect(() => {
  //   fetch("http://127.0.0.1:8000/visualize/") // Adjust URL based on your backend
  //     .then((response) => response.json())
  //     .then((data) => {
  //       setGraphList(data["Possible Graphs"] || []); // Extract list from response
  //     })
  //     .catch((error) => console.error("Error fetching graphs:", error));
  // }, []);

  // Fetch the list of available graphs from the backend with file upload
  const fetchGraphList = async () => {
    if (!file) {
      alert("Please upload a file before fetching graph options.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://127.0.0.1:8000/data_visualization/visualize/", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      setGraphList(data["Possible Graphs"] || []);
      setFileID(data?.file_id)
    } catch (error) {
      console.error("Error fetching graphs:", error);
      alert("Failed to fetch graphs. Please try again.");
    }
  };

   // Handle file selection
   const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setFile(event.target.files[0]);
    }
  };

  // Extract graph type and columns from the selected string
  const parseGraphSelection = (selectionString) => {
    const graphType = selectionString.split("(")[0].trim(); // Extracts "Bar Chart"
    const columnsText = selectionString.match(/\((.*?)\)/)?.[1] || ""; // Extracts text inside ( )
    const [x_axis, y_axis] = columnsText.includes(" vs ")
      ? columnsText.split(" vs ").map((col) => col.trim()) // Extracts X and Y
      : [columnsText.trim(), null]; // Single-column graphs

    return { graph_type: graphType, x_axis, y_axis };
  };

  // Add a new selection block for multiple graphs
  const addGraphSelection = () => {
    setSelectedGraphs([...selectedGraphs, { graph_type: "", x_axis: "", y_axis: "" }]);
  };

  // Handle dropdown selection change
  const handleChange = (index, value) => {
    const { graph_type, x_axis, y_axis } = parseGraphSelection(value);
    const updatedSelections = [...selectedGraphs];
    updatedSelections[index] = { graph_type, x_axis, y_axis };
    setSelectedGraphs(updatedSelections);
  };

  const handleSubmit = async () => {
    if (selectedGraphs.length === 0) {
      alert("Please select at least one graph.");
      return;
    }
  
    if (!file) {
      alert("Please upload a file.");
      return;
    }
  
    // ✅ Create FormData object
    const formData = new FormData();
    formData.append("file", file); // Attach file
    formData.append("graphs", JSON.stringify(selectedGraphs.map(graph => ({
      graph_type: graph.graph_type,
      columns_selected: {
        x_axis: graph.x_axis,
        y_axis: graph.y_axis || null,
      }
    })))); // Convert graphs data to JSON string
  
    setLoading(true);
  
    try {
      const response = await fetch("http://127.0.0.1:8000/data_visualization/generate_graph", {
        method: "POST",
        body: formData,  // ✅ Send as FormData (no Content-Type needed)
      });
  
      const data = await response.json();
      if (data.graphs) {
        setGraphHtml(data.graphs);
      } else {
        alert("Error generating graphs!");
      }
    } catch (error) {
      console.error("Error fetching graphs:", error);
      alert("Failed to fetch graphs. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <h1>Data Visualization</h1>
      {/* File Upload Section */}
      <div className="file-upload">
        <input
          type="file"
          accept=".csv, .xlsx, .json"
          onChange={handleFileChange}
        />
        <button onClick={fetchGraphList}>Upload & Fetch Graph Options</button>
      </div>

      {/* Dynamically add multiple graph selections */}
      {selectedGraphs.map((graph, index) => (
        <div key={index} className="graph-selection">
          <h3>Graph {index + 1}</h3>

          {/* Select Graph Type */}
          <select value={`${graph.graph_type} (${graph.x_axis} ${graph.y_axis ? `vs ${graph.y_axis}` : ""})`}
            onChange={(e) => handleChange(index, e.target.value)}>
            <option value="">-- Choose Graph --</option>
            {graphList.map((g, idx) => (
              <option key={idx} value={`${g["Graph Type"]} (${g.X} ${g.Y ? `vs ${g.Y}` : ""})`}>
                {g["Graph Type"]} ({g.X} {g.Y ? `vs ${g.Y}` : ""})
              </option>
            ))}
          </select>

          {/* Remove Graph Selection */}
          <button onClick={() => setSelectedGraphs(selectedGraphs.filter((_, i) => i !== index))}>
            Remove
          </button>
        </div>
      ))}

      {/* Add More Graphs Button */}
      <button onClick={addGraphSelection}>Add Another Graph</button>

      {/* Submit Button */}
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Generating..." : "Generate Graphs"}
      </button>

      {/* Render the received HTML */}
      <GraphDisplay graphs={graphHtml} />
    </div>
  );
}

export default App;
