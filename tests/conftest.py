import pytest
from py.xml import html

###########################################################################################
## REPORT
###########################################################################################


def stringToCellData(string, class_):
    return html.td([html.p(s) for s in string.split("\n")], class_=class_)


# @pytest.mark.optionalhook
def pytest_html_results_table_header(cells):
    cells.insert(1, html.th("Specification", class_="spec", col="spec"))
    cells.insert(2, html.th("Description"))
    cells.insert(3, html.th("Procedure", class_="proc", col="proc"))
    cells.insert(4, html.th("Expected", class_="expec", col="expec"))
    cells.pop()  # remove links column


# @pytest.mark.optionalhook
def pytest_html_results_table_row(report, cells):
    cells.insert(1, stringToCellData(report.specification, class_="col-spec"))
    cells.insert(2, stringToCellData(report.description, class_="col-desc"))
    cells.insert(3, stringToCellData(report.procedure, class_="col-proc"))
    cells.insert(4, stringToCellData(report.expected, class_="col-expec"))
    cells.pop()  # remove links column


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    report.description = str(item.function.__doc__ if item.function.__doc__ else "")
    marker = item.get_closest_marker("report")

    report.procedure = (
        marker.kwargs["procedure"] if marker and "procedure" in marker.kwargs else ""
    )
    report.expected = (
        marker.kwargs["expected"] if marker and "expected" in marker.kwargs else ""
    )
    report.specification = (
        marker.kwargs["specification"]
        if marker and "specification" in marker.kwargs
        else ""
    )
