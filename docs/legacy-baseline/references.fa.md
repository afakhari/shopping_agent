# منابع رسمی و مراجع فنی

**هدف:** این صفحه لینک‌های اصلی برای implementation و بررسی تغییرات نسخه‌ها را ثبت می‌کند. مستندات آنلاین در طول زمان تغییر می‌کنند؛ نسخه‌های dependency هنگام آغاز توسعه باید بر اساس سازگاری و stable status انتخاب و در lockfile ثبت شوند. متن این صفحه به معنی تأیید اجرای ابزارها روی میزبان نهایی نیست.

## Python و API

- [Python documentation](https://docs.python.org/3/)
- [Django documentation](https://docs.djangoproject.com/en/stable/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Pydantic documentation](https://docs.pydantic.dev/latest/)

## PostgreSQL و جست‌وجو

- [PostgreSQL documentation](https://www.postgresql.org/docs/)
- [`pg_trgm` — similarity and index support](https://www.postgresql.org/docs/current/pgtrgm.html)
- [PostGIS documentation](https://postgis.net/documentation/)
- [PostgreSQL `EXPLAIN`](https://www.postgresql.org/docs/current/using-explain.html)

## Agent و workflow

- [LangGraph overview — Python](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph interrupts / human-in-the-loop](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangChain agents and `create_agent`](https://docs.langchain.com/oss/python/langchain/agents)
- [OpenAI Agents SDK documentation](https://openai.github.io/openai-agents-python/)
- [PydanticAI documentation](https://ai.pydantic.dev/)
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

## Frontend و Generative UI

- [React documentation](https://react.dev/)
- [Vite guide](https://vite.dev/guide/)
- [TypeScript handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [Tailwind CSS documentation](https://tailwindcss.com/docs)
- [shadcn/ui documentation](https://ui.shadcn.com/docs)
- [TanStack Query](https://tanstack.com/query/latest/docs/framework/react/overview)
- [TanStack Query cancellation](https://tanstack.com/query/latest/docs/framework/react/guides/query-cancellation)
- [React Hook Form](https://react-hook-form.com/)
- [Zod](https://zod.dev/)
- [Vercel AI SDK: Generative UI](https://ai-sdk.dev/docs/ai-sdk-ui/generative-user-interfaces)
- [CopilotKit + LangGraph Python](https://docs.copilotkit.ai/langgraph-python)
- [AG-UI protocol](https://docs.ag-ui.com/)
- [A2UI project](https://github.com/google/A2UI)
- [assistant-ui documentation](https://www.assistant-ui.com/docs)

## Docker و استقرار

- [Docker Compose documentation](https://docs.docker.com/compose/)
- [Docker build documentation](https://docs.docker.com/build/)
- [Liara documentation](https://docs.liara.ir/)
- [OWASP API Security Top 10](https://owasp.org/API-Security/)

## نقشه

- [Neshan developer platform](https://platform.neshan.org/)
- [Leaflet documentation](https://leafletjs.com/reference.html)
- [MapLibre GL JS documentation](https://maplibre.org/maplibre-gl-js/docs/)

## قاعده استفاده از منابع

1. برای رفتار وابسته به نسخه، مستندات نسخه تثبیت‌شده در lockfile را مقدم بدانید؛ لینک `stable/latest/current` برای مرور اولیه است.
2. قابلیت‌های سرویس میزبان، region و پلن را با smoke test واقعی تأیید کنید.
3. feature که در صفحه رسمی معرفی شده لزوماً در پلن، کشور، شبکه یا runtime فعلی در دسترس نیست.
4. اگر مرجع رسمی با ADR تعارض دارد، تعارض را بررسی و تصمیم را در ADR به‌روزرسانی کنید؛ کتابخانه‌ای را فقط بر اساس یک blog یا تبلیغ انتخاب نکنید.


## بازبینی نسخه‌های dependency در ۲۱ اکتبر ۲۰۲۶

- Django 6.1.2 طبق release notes رسمی در ۶ اکتبر ۲۰۲۶ منتشر شده است: <https://docs.djangoproject.com/en/6.1/releases/6.1.2/>.
- Django REST framework 3.18.3 از 3.18.2 جدیدتر است؛ release notes رسمی می‌گویند 3.18.3 در ۶ اکتبر منتشر شده و تغییر اشتباه `order_by_precedence` در 3.18.2 را برمی‌گرداند: <https://www.django-rest-framework.org/community/release-notes/>.
- LangGraph 1.2.16 در ۱۶ اکتبر ۲۰۲۶ روی PyPI منتشر شده است: <https://pypi.org/project/langgraph/1.2.16/>.
- React و React DOM به 19.3.1 هم‌تراز شده‌اند؛ صفحات رسمی npm برای هر دو، 19.3.1 را جدیدترین نسخه در زمان بررسی نشان می‌دهند: <https://www.npmjs.com/package/react> و <https://www.npmjs.com/package/react-dom>.
- Vite 8.3.5 و `@vitejs/plugin-react` 6.1.2 در npm ثبت شده‌اند: <https://www.npmjs.com/package/vite> و <https://www.npmjs.com/package/@vitejs/plugin-react>.

این بازبینی، بررسی metadata انتشار است نه آزمون سازگاری runtime پروژه. نصب dependencyها، resolver، `npm ci`, تست و build باید در محیط دارای دسترسی رجیستری اجرا شود؛ این پروژه هنوز به lockfile npm تولیدشده روی همان dependency graph نیاز دارد.

## Design System و کیفیت UI (بازبینی ۲۲ اکتبر ۲۰۲۶)

- [OpenAI Apps SDK UI Guidelines](https://developers.openai.com/plugins/concepts/ui-guidelines) — رفتار کارت‌ها و نمایش‌های درون گفتگو.
- [OpenAI Apps SDK UI](https://github.com/openai/apps-sdk-ui) — توکن‌های رنگ، تایپوگرافی، فاصله و اجزای قابل دسترس.
- [ChatGPT Shopping Research](https://help.openai.com/en/articles/12911370-using-shopping-research-in-chatgpt) — الگوی کشف محصول و مقایسه در گفتگو.
- [Microsoft Fluent 2 Typography](https://fluent2.microsoft.design/typography) — type ramp و hierarchy.
- [Microsoft Fluent 2 Accessibility](https://fluent2.microsoft.design/accessibility) — کنتراست و رفتار قابل دسترس.
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) — استاندارد دسترس‌پذیری وب.
- [Vazirmatn](https://github.com/rastikerdar/vazirmatn) — فونت فارسی/عربی و دستور استفادهٔ وب.
- [OpenAI Frontend prompting guidance](https://developers.openai.com/api/docs/guides/frontend-prompt) — طراحی کاربردی و پرهیز از کارت‌ها و hero تزئینی.
