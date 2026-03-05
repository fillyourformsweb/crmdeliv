import os

path = 'templates/task.html'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the start of the export section - use a very specific marker
start_line = -1
for i, line in enumerate(lines):
    if "// ========== EXPORT FUNCTIONS TO WINDOW ==========" in line:
        start_line = i
        break

if start_line != -1:
    # Keep lines before the marker
    new_content = lines[:start_line]
    
    # Define the clean replacement for the end of the file
    clean_end = """        // ========== EXPORT FUNCTIONS TO WINDOW ==========
        window.sendTaskToOpenPlace = sendTaskToOpenPlace;
        window.showTakeTaskModal = showTakeTaskModal;
        window.showStaffAssignmentModal = showStaffAssignmentModal;
        window.selectAssignment = selectAssignment;
        window.viewTaskDetails = viewTaskDetails;
        window.showCompleteTaskModal = showCompleteTaskModal;
        window.showHoldTaskModal = showHoldTaskModal;
        window.showStatusChangeModal = showStatusChangeModal;
        window.deleteTask = deleteTask;
        window.showCancelTaskModal = showCancelTaskModal;
        window.selectService = selectService;
        window.toggleOnlineForm = toggleOnlineForm;
        window.updateSelfPayFields = updateSelfPayFields;
        window.handleDuePaymentModeChange = handleDuePaymentModeChange;
        window.validateHybridPayment = validateHybridPayment;
        window.showCustomerChatModal = showCustomerChatModal;
        window.copyChatDetails = copyChatDetails;
        window.showStatusChangeWithNotification = showStatusChangeWithNotification;
        window.confirmStatusChangeWithNotification = confirmStatusChangeWithNotification;
        window.printTaskBill = printTaskBill;
        window.generatePdfFromHtml = generatePdfFromHtml;
        window.shareBillWhatsApp = shareBillWhatsApp;
        window.editTask = editTask;
        window.reopenCompletedTask = reopenCompletedTask;
        window.markTaskAsOffer = markTaskAsOffer;

        // Export statistics helpers for other scripts/inline callers
        window.updateTaskStatistics = updateTaskStatistics;
        window.updateStatistics = updateStatistics;
        window.updateStatisticsDisplay = updateStatisticsDisplay;
        window.switchTab = switchTab;
        window.toggleBillDropdown = toggleBillDropdown;
        window.closeBillDropdown = closeBillDropdown;
    </script>
    <!-- Group Chat Widget -->
    {% include 'chat_widget.html' %}
</body>
</html>
"""
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.writelines(new_content)
        f.write(clean_end)
    print(f"Successfully repaired task.html at line {start_line}")
else:
    # Fallback if marker is missing
    print("Could not find export section marker, trying secondary marker...")
    start_line = -1
    for i, line in enumerate(lines):
        if "async function markTaskAsOffer" in line:
            start_line = i
            # Find the end of this function
            brace_count = 0
            found_start = False
            for j in range(i, len(lines)):
                if '{' in lines[j]:
                    brace_count += lines[j].count('{')
                    found_start = True
                if '}' in lines[j]:
                    brace_count -= lines[j].count('}')
                if found_start and brace_count == 0:
                    start_line = j + 1
                    break
            break
    
    if start_line != -1:
        new_content = lines[:start_line]
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(new_content)
            f.write(clean_end)
        print(f"Repaired task.html using secondary marker at line {start_line}")
    else:
        print("CRITICAL: Could not find any suitable point to repair task.html")
