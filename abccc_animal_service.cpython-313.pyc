import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL_PESQUISA = "https://www.cavalocrioulo.org.br/pesquisa/pesquisas.php"
ITENS_DESEJADOS = [4, 6, 8, 10, 12, 14, 16, 18, 21, 23, 25, 27, 29, 31, 33, 35]


def extrair_animais_pagina_print(html):
    soup = BeautifulSoup(html, "html.parser")
    animais = []
    for forte in soup.find_all("strong"):
        nome = forte.get_text(" ", strip=True) or "xxx"
        pai = forte.parent
        texto = pai.get_text(" ", strip=True) if pai else ""
        links = pai.find_all("a") if pai else []
        sbb = links[0].get_text(strip=True) if links else "xxx"
        pelagem = "xxx"
        if "/" in texto:
            partes = texto.split("/")
            if len(partes) > 1:
                pelagem = partes[-1].strip() or "xxx"
        animais.append({"nome": nome, "sbb": sbb or "xxx", "pelagem": pelagem, "texto_completo": texto or "xxx"})
    return animais


def abrir_animal_por_sbb(driver, sbb):
    driver.get(URL_PESQUISA)
    time.sleep(2)
    campo_sbb = driver.find_element(By.ID, "sbb")
    campo_sbb.clear(); campo_sbb.send_keys(sbb); campo_sbb.send_keys(Keys.RETURN)
    time.sleep(4)


def abrir_pagina_imprimir_5g(driver):
    wait = WebDriverWait(driver, 15)
    link_5g = wait.until(EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "quinta_geracao.php")]')))
    driver.get(link_5g.get_attribute("href"))
    wait.until(EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "quinta_geracao.php") and contains(@href, "print=true")]')))
    link_imprimir = driver.find_element(By.XPATH, '//a[contains(@href, "quinta_geracao.php") and contains(@href, "print=true")]')
    url_imprimir = link_imprimir.get_attribute("href")
    driver.get(url_imprimir)
    wait.until(lambda navegador: "print=true" in navegador.current_url)
    time.sleep(2)
    return driver.page_source, url_imprimir


def adicionar_itens(lista_destino, animais, bloco, item_inicial=1, numeros=None):
    numeros = numeros or range(1, len(animais) + 1)
    proximo = item_inicial
    for numero_item in numeros:
        idx = numero_item - 1
        if idx < len(animais):
            animal = animais[idx]
            lista_destino.append({"numero_item": proximo, "bloco": bloco, **animal})
        proximo += 1


def extrair_pedigree_completo(driver, sbb):
    itens = []
    abrir_animal_por_sbb(driver, sbb)
    html_print, _ = abrir_pagina_imprimir_5g(driver)
    animais_principal = extrair_animais_pagina_print(html_print)
    adicionar_itens(itens, animais_principal, "Animal Principal", 1)

    # Pai do animal principal: Item 11 no extrator atual.
    for item_origem, destino, bloco in [(11, 36, "Item 11"), (28, 84, "Item 28")]:
        try:
            sbb_origem = animais_principal[item_origem - 1]["sbb"]
            if not sbb_origem or sbb_origem == "xxx":
                continue
            abrir_animal_por_sbb(driver, sbb_origem)
            html_print, _ = abrir_pagina_imprimir_5g(driver)
            animais_extraidos = extrair_animais_pagina_print(html_print)
            adicionar_itens(itens, animais_extraidos, bloco, destino, ITENS_DESEJADOS)
        except Exception as e:
            itens.append({"numero_item": destino, "bloco": bloco, "nome": "ERRO", "sbb": "", "pelagem": "", "texto_completo": str(e)})
    return itens
