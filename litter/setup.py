from setuptools import setup, find_packages

# 读取并拆分 requirements.txt 文件
with open('requirements.txt') as f:
    requirements = f.readlines()

# 过滤出本地依赖项并将其移除
local_dependencies = [req.strip() for req in requirements if req.startswith('-e')]

# 剩下的正常依赖项
normal_dependencies = [req.strip() for req in requirements if not req.startswith('-e')]

setup(
    name='litter',
    version='0.0.1',
    packages=find_packages(),
    install_requires=normal_dependencies,
    dependency_links=local_dependencies,
)
