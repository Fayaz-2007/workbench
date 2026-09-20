import { useEffect, useRef } from "react";
import type { ChatMessage } from "../../types";
import { UserMessage } from "./UserMessage";
import { AssistantMessage } from "./AssistantMessage";
import { SystemMessage } from "./SystemMessage";
import { ToolMessage } from "./ToolMessage";
import { LoadingMessage } from "./LoadingMessage";
import { ErrorMessage } from "./ErrorMessage";

export function MessageList({ messages, isSending }: { messages: ChatMessage[]; isSending: boolean }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, isSending]);

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-6 md:px-6">
      {messages.map((message) => {
        if (message.status === "error") {
          return <ErrorMessage key={message.id} text={message.errorMessage ?? "Something went wrong."} />;
        }
        switch (message.role) {
          case "user":
            return <UserMessage key={message.id} message={message} />;
          case "assistant":
            return <AssistantMessage key={message.id} message={message} />;
          case "system":
            return <SystemMessage key={message.id} text={message.text ?? ""} />;
          case "tool":
            return <ToolMessage key={message.id} message={message} />;
          default:
            return null;
        }
      })}
      {isSending && <LoadingMessage />}
      <div ref={bottomRef} />
    </div>
  );
}
