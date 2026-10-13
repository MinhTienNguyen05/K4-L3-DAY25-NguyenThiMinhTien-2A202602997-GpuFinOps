def prune_context(chat_history: list[dict], max_tokens: int = 2000) -> list[dict]:
    """
    Cắt tỉa lịch sử hội thoại dựa trên ngưỡng token cho phép,
    giữ lại System Prompt và các câu thoại gần nhất.
    """
    system_prompts = [m for m in chat_history if m["role"] == "system"]
    user_messages = [m for m in chat_history if m["role"] != "system"]

    # Ước tính token thô (1 word ~ 1.3 tokens)
    retained_messages = []
    current_tokens = sum(len(m["content"].split()) * 1.3 for m in system_prompts)

    for msg in reversed(user_messages):
        msg_tokens = len(msg["content"].split()) * 1.3
        if current_tokens + msg_tokens <= max_tokens:
            retained_messages.insert(0, msg)
            current_tokens += msg_tokens
        else:
            break

    return system_prompts + retained_messages

if __name__ == "__main__":
    history = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": "Hello " * 500},
        {"role": "assistant", "content": "Hi there " * 500},
        {"role": "user", "content": "What is FinOps?"}
    ]
    pruned = prune_context(history, max_tokens=200)
    print(f"Original items: {len(history)} -> Pruned items: {len(pruned)}")