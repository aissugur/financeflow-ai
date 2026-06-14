import { useRef, useState } from "react";
import { IconUpload } from "../lib/icons";

// Premium drag-and-drop upload zone. Validation + states live in the parent;
// this just surfaces the file and the drag affordance.
export default function Upload({ onFile, uploading }) {
  const [drag, setDrag] = useState(false);
  const inputRef = useRef(null);

  function handleFiles(files) {
    const file = files?.[0];
    if (file) onFile(file);
  }

  return (
    <div
      className={`upload ${drag ? "drag" : ""}`}
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      <div className="upload-ico">
        <IconUpload size={22} />
      </div>
      <h3>{uploading ? "Processing…" : "Drag & drop a document"}</h3>
      <p>or click to browse · PDF or TXT · up to 10 MB</p>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt"
        hidden
        disabled={uploading}
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
