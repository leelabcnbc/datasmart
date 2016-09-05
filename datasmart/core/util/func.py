def replace_none_args(old_list, default_list):
    assert len(old_list) == len(default_list)
    for idx in range(len(old_list)):
        if old_list[idx] is None:
            old_list[idx] = default_list[idx]
    return old_list