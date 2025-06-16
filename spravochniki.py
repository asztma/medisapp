import pandas as pd
import os
import streamlit as st
from pathlib import Path

base_dir = str(Path.home() / "Documents" / "medisapp")
os.makedirs(os.path.join(base_dir, "dictionaries"), exist_ok=True)

def load_dictionary(filename, key_col=None, value_col=None, is_triple=False):
    try:
        path = os.path.join(base_dir, "dictionaries", filename)
        df = pd.read_csv(path, delimiter=";")
        
        if is_triple:
            return df
        elif value_col:
            return dict(zip(df[key_col], df[value_col]))
        else:
            return df[key_col].tolist()
    except Exception as e:
        st.error(f"Ошибка загрузки справочника {filename}: {e}")
        return pd.DataFrame() if is_triple else ({} if value_col else [])

def save_dictionary(filename, data, columns):
    path = os.path.join(base_dir, "dictionaries", filename)
    pd.DataFrame(data, columns=columns).to_csv(path, index=False, sep=";")

def export_dictionary(filename):
    path = os.path.join(base_dir, "dictionaries", filename)
    try:
        df = pd.read_csv(path, delimiter=";")
        csv = df.to_csv(index=False, sep=";")
        st.download_button(
            label="Скачать справочник",
            data=csv,
            file_name=filename,
            mime="text/csv",
            key=f"export_{filename}"
        )
    except Exception as e:
        st.error(f"Ошибка при экспорте справочника: {e}")

def import_dictionary(filename, columns):
    uploaded_file = st.file_uploader(
        "Выберите CSV файл для импорта", 
        type=["csv"],
        key=f"import_{filename}"
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, delimiter=";")

            if list(df.columns) != columns:
                st.error(f"Неверная структура файла. Ожидаемые колонки: {columns}")
                return
            st.write("Предпросмотр данных для импорта:")
            st.dataframe(df.head())
            
            if st.button(f"Подтвердить импорт {filename}"):
                save_dictionary(base_dir, filename, df, columns)
                st.success("Справочник успешно импортирован!")
                st.rerun()
                
        except Exception as e:
            st.error(f"Ошибка при импорте файла: {e}")

def edit_dictionary_ui(dict_name, config):
    filename = config["filename"]
    columns = config["columns"]
    is_key_only = config.get("key_only", False)
    is_triple = config.get("is_triple", False)
    
    path = os.path.join(base_dir, "dictionaries", filename)
    
    try:
        df = pd.read_csv(path, delimiter=";")
    except:
        df = pd.DataFrame(columns=columns)
    
    st.subheader(f"Редактирование справочника: {dict_name}")
    
    tab1, tab2, tab3 = st.tabs(["Редактирование", "Импорт", "Экспорт"])
    
    with tab1:
        with st.form(key=f"add_{filename}"):
            if is_key_only:
                new_key = st.text_input("Новое значение")
                if st.form_submit_button("Добавить"):
                    if new_key and new_key not in df[columns[0]].values:
                        new_row = {columns[0]: new_key}
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        save_dictionary(filename, df, columns)
                        st.success("Значение добавлено!")
                        st.rerun()
            elif is_triple:
                cols = st.columns(3)
                new_values = []
                for i, col in enumerate(cols):
                    with col:
                        new_values.append(st.text_input(columns[i]))
                
                if st.form_submit_button("Добавить"):
                    if all(new_values):
                        exists = (df[columns[0]] == new_values[0]).any()
                        if not exists:
                            new_row = {columns[i]: new_values[i] for i in range(3)}
                            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                            save_dictionary(filename, df, columns)
                            st.success("Запись добавлена!")
                            st.rerun()
                        else:
                            st.error("Такое подразделение уже существует!")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    new_key = st.text_input(columns[0])
                with col2:
                    new_value = st.text_input(columns[1])
                
                if st.form_submit_button("Добавить"):
                    if new_key and new_value and new_key not in df[columns[0]].values:
                        new_row = {columns[0]: new_key, columns[1]: new_value}
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        save_dictionary(filename, df, columns)
                        st.success("Значение добавлено!")
                        st.rerun()

        st.write("Текущие значения:")
        
        if is_triple:
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    columns[0]: st.column_config.TextColumn(disabled=False),
                    columns[1]: st.column_config.TextColumn(disabled=False),
                    columns[2]: st.column_config.TextColumn(disabled=False)
                }
            )
        elif len(columns) == 2 and not is_key_only:
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    columns[0]: st.column_config.TextColumn(disabled=False),
                    columns[1]: st.column_config.TextColumn(disabled=False)
                }
            )
        else:
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    columns[0]: st.column_config.TextColumn(disabled=False)
                }
            )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Сохранить изменения", key=f"save_{filename}"):
                save_dictionary(filename, edited_df, columns)
                st.success("Изменения сохранены!")
        with col2:
            if st.button("Очистить справочник", key=f"clear_{filename}"):
                if "show_clear_confirm" not in st.session_state:
                    st.session_state.show_clear_confirm = True
                
                if st.session_state.show_clear_confirm:
                    with st.dialog("Подтверждение очистки"):
                        st.warning("Вы уверены, что хотите полностью очистить справочник?")
                        confirm_col1, confirm_col2 = st.columns(2)
                        with confirm_col1:
                            if st.button("Да, очистить"):
                                save_dictionary(filename, [], columns)
                                st.session_state.show_clear_confirm = False
                                st.rerun()
                        with confirm_col2:
                            if st.button("Отмена"):
                                st.session_state.show_clear_confirm = False
                                st.rerun()
        with col3:
            if st.button("Добавить примеры", key=f"example_{filename}") and df.empty:
                example_data = config.get("example_data", [])
                if example_data:
                    save_dictionary(filename, example_data, columns)
                    st.rerun()
    
    with tab2:
        st.subheader("Импорт справочника")
        st.info("Загрузите CSV файл с тем же форматом колонок для замены текущего справочника")
        import_dictionary(filename, columns)
    with tab3:
        st.subheader("Экспорт справочника")
        st.info("Скачайте текущий справочник в CSV файл")
        export_dictionary(filename)

def init_dictionaries():
    os.makedirs(os.path.join(base_dir, "dictionaries"), exist_ok=True)
    
    dictionaries_config = {
        "rashod_bu_to_uu": {
            "filename": "rashod_bu_to_uu.csv",
            "columns": ["Статья затрат БУ", "Статья затрат УУ"],
            "example_data": [
                ["Заработная плата", "Заработная плата УУ"],
                ["Материальные затраты", "Материальные затраты УУ"]
            ]
        },
        
        "nomen_to_business": {
            "filename": "nomen_to_business.csv",
            "columns": ["Номенклатурная группа", "Бизнес-направление"],
            "example_data": [
                ["COVID-19 \"ЛУКОЙЛ\"", "ПБГ Лукойл"],
                ["Вакцинация ЛУКОЙЛ-Грипп", "ПБГ Лукойл"]
            ]
        },
        "subdiv_to_contractor_business": {
            "filename": "subdiv_to_contractor_business.csv",
            "columns": ["Подразделение", "Контрагент", "Бизнес-направление"],
            "is_triple": True,
            "example_data": [
                ["Поликлиника", "ООО «ЛУКОЙЛ КАПИТАЛ»", "ПБГ Лукойл"],
                ["здравпункты ЛУКОЙЛ-ПЕРМЬ", "ООО Росгосстрах", "ДМС_РГС (прочие)"]
            ]
        }
    }
    
    for config in dictionaries_config.values():
        path = os.path.join(base_dir, "dictionaries", config["filename"])
        if not os.path.exists(path):
            save_dictionary(config["filename"], config.get("example_data", []), config["columns"])