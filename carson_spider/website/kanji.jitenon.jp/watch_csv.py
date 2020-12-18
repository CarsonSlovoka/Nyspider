from pathlib import Path
import pandas as pd


def main():
    """
    ['url',
    'unicode', 'jis水準', '漢検級', '学年',
    '部首', '画数', '種別',
    '音読み', '訓読み', '意味',
    '明朝体', '教科書体', '教科書体（筆順）']
    """
    target_file = Path('./output/csv/get_img_url_from_target_url_detail.csv')
    df = pd.read_csv(target_file, header=0, encoding='utf-8', sep='\t')
    filter_empty = None
    for col_name in ('音読み', '訓読み', '意味',):
        filter_empty = filter_empty | (df[col_name].isnull()) if filter_empty is not None else df[col_name].isnull()
    # df_empty_data = df[(df['音読み'].isnull()) | (df['訓読み'].isnull()) | (df['意味'].isnull())]
    df_empty_data = df[filter_empty]
    print(len(df_empty_data))
    df_ok_data = df[~filter_empty]
    df_ok_data.to_csv(target_file.parent/Path(f'temp_{target_file.name}'), index=False, sep='\t')


if __name__ == '__main__':
    main()
