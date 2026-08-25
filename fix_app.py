import re

with open("/home/user/LogicEye-main/frontend/src/App.tsx", "r") as f:
    content = f.read()

content = re.sub(r'(const queryClient = new QueryClient\(\{.*?\n\}\)).*?(function App\(\) \{)', r'\1\n\n\2', content, flags=re.DOTALL)

with open("/home/user/LogicEye-main/frontend/src/App.tsx", "w") as f:
    f.write(content)
