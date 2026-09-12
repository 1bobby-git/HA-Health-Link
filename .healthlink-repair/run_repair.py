"""Reassemble and verify exact public logo transport before applying repairs."""
from pathlib import Path
import hashlib
import runpy

root = Path('.healthlink-repair')
(root/'logo.5.b64').write_text(''.join((root/f'logo.5{part}.txt').read_text() for part in 'abc'))
expected = {
 'icon.0.b64': '192cbf99eb3b4a1ca2eba365409513f724d206414df5d20e5283e0efec00c25b',
 'icon.1.b64': '606bd1f7348f65f6f2f3a266ebdc5cbf24880ee25c3e6e3ffe3b18cc552f4080',
 'icon.2.b64': 'adc17bf08a52f74e702891a12a656dadb24e890647255ac5896640224df22194',
 'icon.3.b64': 'a6647b0df305a46dab5ade445336007f5631a691390ef07cd8e204401f98878d',
 'icon.4.b64': '33f7672a27c6b0bade6cf924d2a21464ffec6452ca5df2c579b1496e1c7132dc',
 'icon.5.b64': '6b8b213e138e93678fd9f3a819a2e455f114d2361860338db12bff53897a9a19',
 'logo.0.b64': '55647be9345b122d1d6aaa3141e5e921334ecdfb2b36a2f3481eec4b6aece700',
 'logo.1.b64': '45fa8fa8dbf75802cb9b1bfea416ccc7961cdcbfe5b2307249ac40c26eef40da',
 'logo.2.b64': 'caf14612a15a6ec95db3b77afe37cc49b1536b338abc2fcb4b8c7c15e1e5627b',
 'logo.3.b64': '0fc784fd7bf3511469ec2188b61e6ad9eede77b772defe4b388a7d4143c3d513',
 'logo.4.b64': '9fc4496db744750fa9de33796d44c0de1919e92a950a56a0b2ac8ba928a63cb0',
 'logo.5.b64': 'a1deae0723684294a39505b98599cafa2b56d9051deb1cba0e9e3ee84196f8e8',
 'logo.6.b64': '1614b136fa34d518cd078095c761070134ba5c7a789d9eb7f76461771b6c920a',
 'logo.7.b64': 'a80a6b5888652282ac2c2ac9cdcc435b7a0f4ed26cba9a2f54e589ba0ceeb4d6',
 'logo.8.b64': '8077cc20fb6d9903f1130dfec046ce2d94780432fc4258e51353f06376d24509',
}
for name, digest in expected.items():
    path = root/name
    text = ''.join(path.read_text().split())
    actual = hashlib.sha256(text.encode()).hexdigest()
    assert actual == digest, f'Logo transport integrity failure: {name} ({actual})'
    path.write_text(text)
print('All 15 approved-artwork transport blocks verified.')
runpy.run_path(str(root/'apply.py'), run_name='__main__')
