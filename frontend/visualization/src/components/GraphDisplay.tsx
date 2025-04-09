import "./GraphDisplay.css";

// Define TypeScript interfaces
interface GraphColumns {
    x_axis: string;
    y_axis?: string | null;
  }
  
  interface GraphData {
    graph_type: string;
    columns: GraphColumns;
    graph_url: string;
  }
  
  interface GraphDisplayProps {
    graphs: GraphData[];
  }

const GraphDisplay: React.FC<GraphDisplayProps> = ({ graphs }) => {
  if (!graphs || graphs.length === 0) {
    return <p className="no-data">No graphs available.</p>;
  }

  return (
    <div className="container">
      <h1 className="title">📊 Generated Graphs</h1>

      <div className="graph-grid">
        {graphs.map((graph , index) => (
          <div key={index} className="graph-card">
            <h3 className="graph-title">{graph.graph_type}</h3>
            <p className="graph-info">
              <strong>X-Axis:</strong> {graph.columns.x_axis}
              {graph.columns.y_axis && (
                <>
                  {" "}
                  | <strong>Y-Axis:</strong> {graph.columns.y_axis}
                </>
              )}
            </p>
            <div className="graph-image-container">
              <img
                src={graph.graph_url}
                alt={`${graph.graph_type} Graph`}
                className="graph-image"
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default GraphDisplay;
