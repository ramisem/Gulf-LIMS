document.addEventListener("DOMContentLoaded", function () {
    console.log("Amendment script loaded");
    const actionBtn = document.querySelector("button[name='index']");
    console.log("Go button found:", actionBtn);
    const confirmBtn = document.getElementById("confirmAmendment");
    const cancelBtn = document.getElementById("cancelAmendment");
    const modal = document.getElementById("amendmentModal");
    const overlay = document.getElementById("modalOverlay");
    let selectedIds = [];
    actionBtn.addEventListener("click", function (e) {
        console.log("Go button clicked");
       const actionSelect = document.querySelector("select[name='action']");
       if (actionSelect && actionSelect.value === "amend_report") {
           const checkboxes = document.querySelectorAll("input.action-select:checked");
           if (checkboxes.length > 0) {
                e.preventDefault();
                selectedIds = Array.from(checkboxes).map(cb => cb.value);
                  const inputURL = `${window.location.origin}/analysis/get_amendment_types/`;
                $.ajax({
                    url: inputURL,
                    type: 'GET',
                    dataType: 'json',
                    success: function (data) {
                        const select = document.getElementById("amendmentTypeSelect");
                        select.innerHTML = "";

                        if (!data.amendment_types || data.amendment_types.length === 0) {
                            alert("No amendment types available.");
                            return;
                        }

                        data.amendment_types.forEach(item => {
                            const opt = document.createElement("option");
                            opt.value = item.value;
                            opt.textContent = item.display_value;
                            select.appendChild(opt);
                        });

                        document.getElementById("amendmentModal").style.display = "block";
                        document.getElementById("modalOverlay").style.display = "block";

                    },
                    error: function (error) {
                        console.error('Error fetching Amendment Types:', error);
                    }
                });
           }
       }
    });
    cancelBtn.addEventListener("click", function () {
        document.getElementById("amendmentModal").style.display = "none";
        document.getElementById("modalOverlay").style.display = "none";
    });
    confirmBtn.addEventListener("click", function () {
        const selectedType = document.getElementById("amendmentTypeSelect").value;

        if (!selectedType) {
            alert("Please select an amendment type.");
            return;
        }

        const postURL = "/analysis/amend-report-action/";
        $.ajax({
            url: postURL,
            type: "POST",
            headers: {
                "X-CSRFToken": getCSRFToken()
            },
            data: JSON.stringify({
                selected_ids: selectedIds,
                amendment_type: selectedType
            }),
            contentType: "application/json",
            success: function (data) {
                document.getElementById("amendmentModal").style.display = "none";
                document.getElementById("modalOverlay").style.display = "none";

                if (data.status === "success") {
                    alert(`Amendment applied to ${data.updated} item(s).`);
                    window.location.reload();
                } else {
                    alert("Error: " + data.error);
                }
            },
            error: function (err) {
                console.error("Error submitting amendment:", err);
                alert("An error occurred while submitting the amendment.");
                document.getElementById("amendmentModal").style.display = "none";
                document.getElementById("modalOverlay").style.display = "none";
            }
        });
    });

    // CSRF helper
    function getCSRFToken() {
        const name = "csrftoken";
        const cookies = document.cookie.split(";").map(c => c.trim());
        for (let cookie of cookies) {
            if (cookie.startsWith(name + "=")) {
                return decodeURIComponent(cookie.slice(name.length + 1));
            }
        }
        return "";
    }
});



