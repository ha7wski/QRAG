"""
synthesis_prompt.py — Builds the LLM prompt for the *madār* synthesis.

The model is given ONLY verified inputs — Ibn Fāris' real aṣl (when present) and
the root's actual Quranic occurrences (surface + reference + short context) — and
asked to distill the common pivot (مدار) in Arabic, grounded strictly in those
inputs. It must never introduce lexical claims beyond what is provided; if the
aṣl is absent it must say so and lean on the occurrences alone.

Arabic-only is enforced twice: an explicit instruction here, and a deterministic
post-check in `madar_service` that voids any drifted (non-Arabic) output.
"""
from __future__ import annotations

# Hard system contract. Kept terse and imperative — qwen2.5:7b drifts (Chinese /
# Latin fragments) on long, chatty prompts; a tight instruction curbs that.
SYSTEM_PROMPT = (
    "أنت باحث لغوي دقيق. مهمتك أن تستخلص «المدار»، أي المعنى المحوري الجامع، "
    "لجذر عربي، اعتمادًا فقط على ما يُعطى لك: أصل ابن فارس (إن وُجد) ومواضع "
    "ورود الجذر في القرآن.\n"
    "قواعد ملزمة:\n"
    "١) لا تُضِف أي معلومة من خارج الأصل المُعطى والمواضع المُعطاة. لا تخترع "
    "اشتقاقات ولا معاني جديدة.\n"
    "٢) أجب بالعربية الفصحى فقط. لا تستعمل أي حرف لاتيني أو صيني أو أرقامًا "
    "أجنبية.\n"
    "٣) إن كان أصل ابن فارس غائبًا، فابنِ المدار على المواضع القرآنية وحدها، "
    "وصرّح بذلك.\n"
    "٤) اجعل الجواب فقرة واحدة موجزة (نحو ثلاثة أسطر) تصف المعنى المحوري، "
    "دون تكرار قائمة المواضع.\n"
)


def _occurrence_line(occ: dict) -> str:
    """One compact occurrence line: surface — surah:ayah — (short context)."""
    surface = occ.get("surface") or ""
    ref = f"{occ.get('surah')}:{occ.get('ayah')}"
    context = (occ.get("context") or "").strip()
    base = f"- {surface} [{ref}]"
    return f"{base}: {context}" if context else base


def build_user_message(
    root: str,
    asl_text: str | None,
    occurrences: list[dict],
    occurrences_count: int,
) -> str:
    """Assemble the user turn from the verified inputs.

    `asl_text` is Ibn Fāris' cited sentence (or None/"" when unavailable).
    `occurrences` is the representative SAMPLE (surface, surah, ayah, context);
    `occurrences_count` is the true total, stated so the model knows the sample
    is partial."""
    lines: list[str] = [f"الجذر: {root}"]
    if asl_text:
        lines.append(f"\nأصل ابن فارس (نصٌّ مُوثَّق): «{asl_text}»")
    else:
        lines.append(
            "\nأصل ابن فارس: غير متوفّر لهذا الجذر — اعتمد على المواضع وحدها "
            "وصرّح بذلك."
        )
    total = occurrences_count or len(occurrences)
    shown = len(occurrences)
    lines.append(
        f"\nمواضع ورود الجذر في القرآن (عيّنة من {shown} من أصل {total} موضعًا):"
    )
    lines.extend(_occurrence_line(o) for o in occurrences)
    lines.append("\nاستخلص المدار الجامع وفق القواعد أعلاه.")
    return "\n".join(lines)
