import React from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center p-6">
      <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 font-mono text-2xl mb-4 font-bold">
        404
      </div>
      <h2 className="text-xl font-bold text-slate-800 mb-1">Operational Route Not Found</h2>
      <p className="text-sm text-slate-500 max-w-sm mb-6">
        The requested view does not exist within the AirOps Nexus mission architecture.
      </p>
      <Link to="/">
        <Button variant="primary">Return to Operations Overview</Button>
      </Link>
    </div>
  );
};
