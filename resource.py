with st.sidebar.expander("📦 Resources", expanded=False):
    st.markdown("### Registered Resources")
    for r in mcp_data["resources"]:
        st.markdown(f"**{r['name']}**\n\n{r['description']}")

    if mcp_data["yaml"]:
        st.markdown("---")
        st.markdown("### 📄 Schematic Models (YAML)")
        for y in mcp_data["yaml"]:
            st.code(y, language="yaml")
