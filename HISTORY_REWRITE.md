# Published history rewrite (2026-10-06): old → new commit hashes

**Status:** provenance record. Not a research result; it changes no specification, code, data, result or methodology (`RESEARCH_DECISIONS.md` D-26).

## What changed

On 2026-10-06 the published histories of `chethana100/uwsn` (`main`) and `chethana100/aqua-sim-ng` (`master`) were rewritten to remove the unintended commit-message trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` from 25 parent commits and 2 submodule commits. Nothing else changed:
- Author and committer names, emails and timestamps: identical.
- File contents: identical. Submodule trees are identical; parent trees differ only in the `src/aqua-sim-ng` submodule pointer (gitlink), remapped to the rewritten submodule commits.
- Commit messages: identical apart from removal of that trailer line and the blank line before it. Hashes cited inside messages were kept verbatim (`--preserve-commit-hashes`).
- Research results: unchanged; no file content changed.
- Not rewritten: the three `chethana100` parent commits (`9821ba8`, `2719461`, `370d2e6`) and all 276 earlier aqua-sim-ng commits, including 13 signed upstream commits.

**Method:** git filter-repo 2.34.0, limited to `370d2e6..main` and `fa2e87d..master`. Rehearsed and validated in disposable clones; pushed with `--force-with-lease`, submodule first. Validation, for every rewritten commit: identical author, committer and raw timestamps; identical tree apart from the remapped gitlink; message difference limited to the removed trailer and the blank line before it; zero Claude trailers remaining in either published history; history linear, with no merges introduced.

## Citation rule

Every commit hash cited in a record written before this rewrite (documents, frozen specifications, code, result artefacts including their `parent_commit` / `submodule_commit` fields, and commit messages) refers to the pre-rewrite commit. Such citations are intentionally left unchanged; resolve them with the tables below. Every file md5 cited in the records remains valid, because no file content changed.

## Submodule (`aqua-sim-ng`, `master`)

| Old | New |
|---|---|
| `b85e98a409c0f3e29be4930832be3798d20c7b90` | `5c1399b5dfae4285a28b80174f427d6cf2f60d0b` |
| `41c67c39e3acd3153bcb16558c11a7b58001b033` | `db72cabef7811b7e9892ef799908e9a7b761de05` |

## Parent (`uwsn`, `main`), oldest first

| Old | New |
|---|---|
| `1e782e8a076549820dd51819cf97e09d0ff52bba` | `36d7dcd5f07d5b0742b5040de5ca93a0b6e23046` |
| `46594aa9442c67a05b1e27b1f72a24476c2a57b2` | `aab37b98b81fd0a92add1e2a56c4f33fc5e09da4` |
| `c0d2cec9c67a62425bd87315f22890d792a1216e` | `d5cc179d915259072f95fb5724722d4970a4be55` |
| `58cc50cffbb1c515da9c01557aef72ec01416732` | `f81d43082fc423f70dff9f2a4e78238ebeabdd82` |
| `e9ddf04b1a20d55574aaf52be6c2af136f5e4caa` | `6df69300ada758bfd000252963e9e62cb97d17a6` |
| `b016a9a0d0bffe6f51af2e0ffc6372449d81da99` | `1341cf4155f5cf72938aeb1b74a024d48211f242` |
| `8a0ff2f46cf434c09f7144f5e768d455278e0151` | `eaf5a563d7240700912b9dd0e6ea520402934169` |
| `c2a5077f4f079d04d4da819cb389f138ab628959` | `5a4f08626e6dc24d70918dbedb8ae7a6756521e4` |
| `103e671eae24e94095fa1164b383148575d46827` | `a1dd48668bc3b45fd3bf6a98e43428ef451a6738` |
| `362cda7a84e8e745ff667d47e13ce31353681350` | `946ee026c0a656a8ed383cabc83da7c5b47e1e42` |
| `a87ffbca52f0fbe7ca6485b14fcaed0c2567620c` | `4b9bb91a6f6e26b94678e9d9cf56ca13e0f949fb` |
| `4a17048a964f41f7f0846d4076cc2aa09888edc9` | `22556e9eb85fbb0172cd442edb1c7fa3ca535272` |
| `36655b739d1350db65c92445b6000c06a5abe87b` | `41b72e01483f192a4f3c389f89206f7baf975135` |
| `ca1edc7493c37168544d5bada58dac8b44249269` | `7569b3bef5eb00c0109043ecda925615c4b27fb3` |
| `3eba65425ce90d95f07aa1bd5ce2f5a4a98d6e08` | `898fee706eea9a9dc0af5be168726f06e282c5b4` |
| `27f98ad75cc11dd46939aa23401bf8527157f9e6` | `195320e27d9c522b3f35144757a9622db55b8bdf` |
| `f8cec329a76482faa3b4eda72d6e2ddbbbce58aa` | `1f8cb3c885d87bff79443562394c78100ab7b7ef` |
| `98bfcf28ef0cbcaaf770d281e5e6f5e774657178` | `89bb054d3cb52d4b22bf41c32f34365ad809885d` |
| `aedeb3a22cf5710f312277cd2dc782198c157187` | `359805697b2e09c105a8d443f0e29be58506ce67` |
| `a984fc7ef17c8bfc17b3d3e4f74c8e235e09b0b8` | `996930e236b3b4d491a4feb9d09d216ee401b1dd` |
| `6c455b069bc20a773c17cb9c7dcae4ff14fb6a52` | `6ae9c53b43e4f11b5c9dc9152f82c05a37cd2998` |
| `4dd4962fe8423b5445d3792bcf4e39f4852405db` | `50d704c9830b7a5c1743fbc52496b72f4623f1a1` |
| `eebbc867af5a70107698402c8a1109758c9b6845` | `fa53a30b13383c89ba7ca04a6341644533cfba4a` |
| `cf7196a60efcdcf2b528d3165228e8281f1fa842` | `166bda77a72b4938604426cc842050940ab49632` |
| `be9c68017db0ffb0648d958602ef57fbb841e7cb` | `1e8a27a092cc7ba6c60be5aafb6be2d51b88132a` |

**Old tips:** `main` `be9c68017db0ffb0648d958602ef57fbb841e7cb`; `master` `41c67c39e3acd3153bcb16558c11a7b58001b033`.
**New tips:** `main` `1e8a27a092cc7ba6c60be5aafb6be2d51b88132a`; `master` `db72cabef7811b7e9892ef799908e9a7b761de05`.
**Source:** git filter-repo commit maps (`uwsn` md5 `5e44c4f2aca36aaa185ee846544e244f`; `aqua-sim-ng` md5 `d1f2ccdf19499332b45070b3a213106d`).
