"use client";

interface TextDiffProps {
  oldText: string | null | undefined;
  newText: string | null | undefined;
}

export default function TextDiff({ oldText, newText }: TextDiffProps) {
  const cleanOld = oldText?.trim() || "";
  const cleanNew = newText?.trim() || "";

  if (!cleanOld && !cleanNew) {
    return <span className="text-zinc-500 text-xs font-mono">No text available to compare</span>;
  }

  // Simple token-based word diff for basic visual markup
  const oldWords = cleanOld.split(/\s+/);
  const newWords = cleanNew.split(/\s+/);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
      <div className="bg-red-950/20 border border-red-500/10 p-3 rounded-lg">
        <p className="text-[10px] text-red-400 font-bold uppercase tracking-wider mb-2">
          Before (Scraped Value)
        </p>
        <div className="text-red-200/80 leading-relaxed break-words whitespace-pre-wrap">
          {oldWords.map((word, idx) => {
            const isRemoved = !newWords.includes(word);
            return (
              <span
                key={idx}
                className={isRemoved ? "bg-red-500/30 text-red-100 px-0.5 rounded" : ""}
              >
                {word}{" "}
              </span>
            );
          })}
        </div>
      </div>

      <div className="bg-emerald-950/20 border border-emerald-500/10 p-3 rounded-lg">
        <p className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider mb-2">
          After (Detected Value)
        </p>
        <div className="text-emerald-200/80 leading-relaxed break-words whitespace-pre-wrap">
          {newWords.map((word, idx) => {
            const isAdded = !oldWords.includes(word);
            return (
              <span
                key={idx}
                className={isAdded ? "bg-emerald-500/30 text-emerald-100 px-0.5 rounded" : ""}
              >
                {word}{" "}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}
