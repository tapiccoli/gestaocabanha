"""Componentes simples para linha do tempo de eventos."""

import streamlit as st


def render_timeline(eventos):
    if not eventos:
        st.info("Nenhum evento registrado ainda.")
        return
    for ev in eventos:
        st.markdown(
            f"""
            <div class='card'>
              <div class='small-label'>{ev.get('data_evento') or ''} • {ev.get('modulo_origem') or ''}</div>
              <div class='big-value'>{ev.get('tipo_evento') or 'Evento'}</div>
              <div>{ev.get('descricao') or ''}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
