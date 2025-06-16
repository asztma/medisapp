import streamlit as st
import pandas as pd
import os
from io import BytesIO
from spravochniki import load_dictionary, edit_dictionary_ui, init_dictionaries
from pathlib import Path

base_dir = str(Path.home() / "Documents" / "medisapp")
os.makedirs(os.path.join(base_dir, "dictionaries"), exist_ok=True)

init_dictionaries()

# Загрузка справочников
ref_city = load_dictionary("Филиалы.csv", "Наименование")
nomen_to_business = load_dictionary("nomen_to_business.csv", "Номенклатурная группа", "Бизнес-направление")
nomen_to_service_type = load_dictionary("nomen_to_service_type.csv", "Номенклатурная группа", "Вид услуг")
business_to_counterparty = load_dictionary("business_to_counterparty.csv", "Бизнес-направление", "Контрагент")
profile_to_med_direction = load_dictionary("profile_to_med_direction.csv", "Профиль", "Направление медицинских услуг")

# Функции валидации
def validate_city(city_value):
    return city_value in ref_city

def validate_amount(amount_value):
    try:
        float(amount_value)
        return True
    except ValueError:
        return False

def validate_nomen_group(nomen_value):
    return nomen_value in nomen_to_business.keys()

def trim_all_cells(df):
    # Применяем strip() ко всем строковым колонкам
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
    return df

# Интерфейс Streamlit
st.title("Проверка Excel-файла")

# Создаем вкладки
tab1, tab2 = st.tabs(["Проверка файлов", "Управление справочниками"])

with tab1:
    st.write("Загрузите файл для проверки")
    
    def download_template():
        template_df = pd.DataFrame(columns=[
            "Филиал", "Сумма", "Подразделение", 
            "Номенклатурная группа", "Профиль", "Статья затрат", "НД"
        ])
        
        example_data = {
            "Филиал": [''],
            "Дата": [''],
            "Сумма": [''],
            "Номенклатурная группа": [''],
            "Вид услуг": [''],
            "Бизнес-направление": [''],
            "Профиль": [''],
            "Направление медицинских услуг": [''],
            "Контрагенты": [''],
            "НД": ['']
        }
        
        template_df = pd.DataFrame(example_data)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            template_df.to_excel(writer, index=False)
        
        return output.getvalue()

    st.download_button(
        label="Скачать шаблон файла",
        data=download_template(),
        file_name='template.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    uploaded_file = st.file_uploader("Выберите Excel файл", type=['xlsx', 'xls'])

    month = st.selectbox("Выберите месяц", 
                       ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"])
    year = st.selectbox("Выберите год", range(2020, 2031))

    if uploaded_file is not None:
        try:

            df = pd.read_excel(uploaded_file)

            df = trim_all_cells(df)
            # Удаляем столбец Дата, если он есть
            if "Дата" in df.columns:
                df = df.drop(columns=["Дата"])
            
            
            # Обязательные колонки, которые должны быть в загружаемом файле
            required_input_columns = [
                "Филиал", "Сумма", 
                "Номенклатурная группа", "Профиль"
            ]
            
            # Проверка наличия обязательных колонок в загруженном файле
            missing_columns = [col for col in required_input_columns if col not in df.columns]
            if missing_columns:
                st.error(f"В файле отсутствуют обязательные столбцы: {', '.join(missing_columns)}")
                st.error("Пожалуйста, используйте предоставленный шаблон.")
            else:
                errors = []
                
                # Добавляем новые столбцы сгенерированными данными
                df["Бизнес-направление"] = df["Номенклатурная группа"].map(nomen_to_business)
                df["Вид услуг"] = df["Номенклатурная группа"].map(nomen_to_service_type)
                
                # Новое правило для пустых номенклатурных групп
                empty_nomen_mask = df["Номенклатурная группа"].isna()
                df.loc[empty_nomen_mask, "Бизнес-направление"] = "управление"
                df.loc[empty_nomen_mask, "Вид услуг"] = pd.NA
                
                df["Контрагенты"] = df["Бизнес-направление"].map(business_to_counterparty)
                df["Направление медицинских услуг"] = df["Профиль"].map(profile_to_med_direction)
                
                for idx, row in df.iterrows():
                    if not validate_city(row["Филиал"]):
                        errors.append(f"Ошибка в строке {idx + 2}, Филиал: '{row['Филиал']}' не соответствует справочнику")                 
                    if not validate_amount(row["Сумма"]):
                        errors.append(f"Ошибка в строке {idx + 2}, Сумма: '{row['Сумма']}' - отрицательное значение или не число")                   
                    if pd.notna(row["Номенклатурная группа"]) and not validate_nomen_group(row["Номенклатурная группа"]):
                        errors.append(f"Ошибка в строке {idx + 2}, Номенклатурная группа: '{row['Номенклатурная группа']}' не соответствует допустимым значениям")                    
                    if pd.notna(row["Номенклатурная группа"]):
                        if pd.isna(row["Бизнес-направление"]):
                            errors.append(f"Ошибка в строке {idx + 2}, Не удалось определить бизнес-направление для номенклатурной группы: '{row['Номенклатурная группа']}'")
                        if pd.isna(row["Вид услуг"]):
                            errors.append(f"Ошибка в строке {idx + 2}, Не удалось определить вид услуг для номенклатурной группы: '{row['Номенклатурная группа']}'")
                    
                    all_counterparties = set(business_to_counterparty.values())

                    def validate_counterparty(counterparty_value, all_counterparties):
                        if pd.isna(counterparty_value):
                            return False
                        return any(str(counterparty) in str(counterparty_value) for counterparty in all_counterparties)
                    if not validate_counterparty(row["Контрагенты"], all_counterparties):
                        errors.append(f"Ошибка в строке {idx + 2}, Не удалось найти допустимого контрагента в ячейке: '{row['Контрагенты']}' для бизнес-направления: '{row['Бизнес-направление']}'")
                    if pd.notna(row["Профиль"]) and pd.isna(row["Направление медицинских услуг"]):
                        errors.append(f"Ошибка в строке {idx + 2}, Не удалось определить направление медицинских услуг для профиля: '{row['Профиль']}'")
                
                if errors:
                    st.error("Найдены ошибки в файле:")
                    for error in errors:
                        st.write(error)
                    
                    errors_df = pd.DataFrame(errors, columns=["Ошибки"])
                else:
                    st.success("Файл проверен успешно. Ошибок не найдено.")
                    
                    month_year_row = pd.DataFrame({
                        col: [""] * len(df.columns) for col in df.columns
                    })
                    month_year_row.iloc[0, 0] = f"{month} {year}"
                    df_with_date = pd.concat([df, month_year_row], ignore_index=True)
                    
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_with_date.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="Скачать обработанный файл",
                        data=output.getvalue(),
                        file_name='processed_file.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                
                st.write("Первые строки загруженного файла (после обработки):")
                st.dataframe(df.head())
        
        except Exception as e:
            st.error(f"Ошибка при обработке файла: {e}")

CORRECT_PASSWORD = "34medisadmin"

def check_password():
    """Проверяет пароль и возвращает True если он верный"""
    if 'password_verified' not in st.session_state:
        st.session_state.password_verified = False
    
    if not st.session_state.password_verified:
        st.warning("Для доступа к управлению справочниками введите пароль")
        password = st.text_input("Пароль:", type="password", key="pwd_input")
        
        if st.button("Войти"):
            if password == CORRECT_PASSWORD:
                st.session_state.password_verified = True
                st.rerun()
            else:
                st.error("Неверный пароль. Попробуйте снова.")
        return False
    return True


with tab2:
    if check_password():
        st.title("Управление справочниками")
        dictionary_configs = {
            "Номенклатура -> Бизнес": {
                "filename": "nomen_to_business.csv",
                "columns": ["Номенклатурная группа", "Бизнес-направление"]
            },
            "Номенклатура -> Вид услуг": {
                "filename": "nomen_to_service_type.csv",
                "columns": ["Номенклатурная группа", "Вид услуг"]
            },
            "Бизнес -> Контрагент": {
                "filename": "business_to_counterparty.csv",
                "columns": ["Бизнес-направление", "Контрагент"]
            },
            "Профиль -> Мед. направление": {
                "filename": "profile_to_med_direction.csv",
                "columns": ["Профиль", "Направление медицинских услуг"]
            },
            "Филиалы": {
                "filename": "Филиалы.csv",
                "columns": ["Наименование"],
                "key_only": True
            }
        }
        
        dict_to_edit = st.selectbox(
            "Выберите справочник для редактирования",
            list(dictionary_configs.keys())
        )
        
        edit_dictionary_ui(dict_to_edit, dictionary_configs[dict_to_edit])