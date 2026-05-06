import type { LLMProvider } from "../types/pipeline";

type Props = {
  logs: string[];
  model: LLMProvider;
};

export default function AgentLogs({ logs, model }: Props) {
  const visibleLogs = [`Using model: ${model}`, ...logs.filter((log) => !log.startsWith("Using model:"))];

  return (
    <details className="agent-logs">
      <summary>查看执行日志</summary>
      <ul>
        {visibleLogs.map((log, index) => (
          <li className={log.startsWith("Using model:") ? "model-log" : ""} key={`${log}-${index}`}>
            {log.startsWith("Using model:") ? log : `→ ${log}`}
          </li>
        ))}
      </ul>
    </details>
  );
}
